import json
import os
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

for k in ("DEEPSEEK_API_KEY", "NEWSAPI_KEY", "GROQ_API_KEY", "GEMINI_API_KEY"):
    os.environ.setdefault(k, "dummy")
import ai
import news_digest as nd


def resp(status=200, content=None, finish="stop", prompt=10, completion=20):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = ({"choices": [{"message": {"content": content}, "finish_reason": finish}],
                            "usage": {"prompt_tokens": prompt, "completion_tokens": completion}}
                           if status == 200 else {"error": "boom"})
    return r


def host(call):
    return call.args[0].split("/")[2]


def setup_function():
    ai.USAGE.clear()


def test_falls_back_to_next_provider_on_http_error():
    with patch("ai.requests.post", side_effect=[resp(500), resp(content='{"x": 1}')]) as p:
        out, who = ai.chat_json("q", 100)
    assert (out, who) == ({"x": 1}, "gemini")
    assert [host(c) for c in p.call_args_list] == ["api.deepseek.com", "generativelanguage.googleapis.com"]


def test_retries_same_provider_with_double_tokens_when_cut_off():
    with patch("ai.requests.post", side_effect=[resp(content='{"x"', finish="length"), resp(content='{"x": 2}')]) as p:
        out, who = ai.chat_json("q", 1000)
    assert (out, who) == ({"x": 2}, "deepseek")
    assert [c.kwargs["json"]["max_tokens"] for c in p.call_args_list] == [1000, 2000]


def test_invalid_answer_moves_to_next_provider():
    with patch("ai.requests.post", side_effect=[resp(content='{"x": 0}'), resp(content='{"x": 3}')]):
        out, who = ai.chat_json("q", 100, validate=lambda d: None if d["x"] else "zero")
    assert (out, who) == ({"x": 3}, "gemini")


def test_all_providers_fail_returns_none():
    with patch("ai.requests.post", return_value=resp(500)):
        assert ai.chat_json("q", 100) == (None, None)
    assert ai.usage_summary()["failed_calls"] == 3


def test_skips_provider_without_key():
    with patch.dict(os.environ, {"DEEPSEEK_API_KEY": ""}), \
         patch("ai.requests.post", return_value=resp(content='{"x": 1}')) as p:
        _, who = ai.chat_json("q", 100)
    assert who == "gemini" and p.call_count == 1


def test_thinking_turned_off_for_deepseek_and_gemini():
    with patch("ai.requests.post", side_effect=[resp(500), resp(content='{"x": 1}')]) as p:
        ai.chat_json("q", 100)
    deepseek_body, gemini_body = (c.kwargs["json"] for c in p.call_args_list)
    assert deepseek_body["model"] == "deepseek-flash" and deepseek_body["thinking"] == {"type": "disabled"}
    assert gemini_body["reasoning_effort"] == "none"


def test_usage_cost_half_price_off_peak():
    ai.USAGE.extend([{"provider": "deepseek", "ok": True, "label": "a", "prompt_tokens": 1_000_000, "completion_tokens": 1_000_000}])
    sunday = datetime(2026, 9, 13, 23, 0, tzinfo=timezone.utc)
    monday_peak = datetime(2026, 9, 14, 2, 0, tzinfo=timezone.utc)
    assert ai.usage_summary(sunday)["deepseek_cost_usd"] == 0.75
    assert ai.usage_summary(monday_peak)["deepseek_cost_usd"] == 1.5


def test_dedupe_by_url_and_title_suffix():
    news = [
        {"title": "Ebola spreads - AP News", "url": "https://a/1"},
        {"title": "Ebola spreads", "url": "https://b/2"},
        {"title": "Other story", "url": "https://a/1"},
        {"title": "Fresh story", "url": "https://c/3"},
    ]
    assert [n["url"] for n in nd.dedupe_news(news)] == ["https://a/1", "https://c/3"]


def test_category_validator():
    check = nd.category_validator(2)
    ok = {"analysis": "x" * 60, "summaries": ["a", "b"], "details": ["c", "d"]}
    assert check(ok) is None
    assert "summaries" in check({**ok, "summaries": ["a"]})
    assert "empty" in check({**ok, "details": ["c", " "]})
    assert "analysis" in check({**ok, "analysis": "short"})


def test_failed_category_publishes_items_without_error_text():
    cat = nd.build_category("ทั่วไป", [{"title": "t", "source": "s", "url": "u"}], None)
    assert cat["analysis"] == "" and cat["items"][0]["summary_th"] is None and cat["count"] == 1


def test_reclassify_keeps_newsapi_tags_when_ai_fails():
    news = [{"title": "x", "desc": "y", "cat": "โรคระบาด"}]
    with patch("ai.requests.post", return_value=resp(500)):
        assert nd.reclassify_categories(news)[0]["cat"] == "โรคระบาด"


def test_reclassify_moves_offtopic_article():
    news = [{"title": "Ebola", "desc": "", "cat": "โรคระบาด"}, {"title": "$10m Ultimate Championship", "desc": "", "cat": "โรคระบาด"}]
    with patch("ai.requests.post", return_value=resp(content=json.dumps({"0": "โรคระบาด", "1": "ทั่วไป"}))) as p:
        out = nd.reclassify_categories(news)
    assert [n["cat"] for n in out] == ["โรคระบาด", "ทั่วไป"]
    assert host(p.call_args_list[0]) == "api.groq.com"


if __name__ == "__main__":
    tests = [v for k, v in dict(globals()).items() if k.startswith("test_")]
    for t in tests:
        setup_function()
        t()
    print(f"OK: {len(tests)} tests passed")
