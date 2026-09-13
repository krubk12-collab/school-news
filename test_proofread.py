import json
import os
from unittest.mock import patch, MagicMock

os.environ.setdefault("DEEPSEEK_API_KEY", "dummy")
os.environ.setdefault("NEWSAPI_KEY", "dummy")
os.environ.setdefault("GROQ_API_KEY", "dummy")
import news_digest


def test_proofread_returns_fixed_text():
    fake_response = MagicMock()
    fake_response.json.return_value = {
        "choices": [{"message": {"content": json.dumps(
            {"analysis": "แก้แล้ว", "summaries": ["ก", "ข"], "details": ["ก detail", "ข detail"]}
        )}}]
    }
    with patch("news_digest.requests.post", return_value=fake_response):
        analysis, summaries, details = news_digest.proofread_thai("ผิด", ["a", "b"], ["a detail", "b detail"])
    assert analysis == "แก้แล้ว"
    assert summaries == ["ก", "ข"]
    assert details == ["ก detail", "ข detail"]


def test_proofread_falls_back_on_mismatched_length():
    fake_response = MagicMock()
    fake_response.json.return_value = {
        "choices": [{"message": {"content": json.dumps({"analysis": "แก้แล้ว", "summaries": ["ก"], "details": ["x"]})}}]
    }
    with patch("news_digest.requests.post", return_value=fake_response):
        analysis, summaries, details = news_digest.proofread_thai("ผิด", ["a", "b"], ["d1", "d2"])
    assert summaries == ["a", "b"]
    assert details == ["d1", "d2"]  # ความยาวไม่ตรง -> fallback ต้นฉบับ


def test_proofread_falls_back_on_error():
    with patch("news_digest.requests.post", side_effect=Exception("boom")):
        analysis, summaries, details = news_digest.proofread_thai("ต้นฉบับ", ["a"], ["d"])
    assert analysis == "ต้นฉบับ"
    assert summaries == ["a"]
    assert details == ["d"]


def test_proofread_skips_when_no_groq_key():
    with patch.object(news_digest, "GROQ_API_KEY", None), \
         patch("news_digest.requests.post") as mock_post:
        analysis, summaries, details = news_digest.proofread_thai("ต้นฉบับ", ["a"], ["d"])
    mock_post.assert_not_called()
    assert analysis == "ต้นฉบับ"
    assert summaries == ["a"]
    assert details == ["d"]


def test_reclassify_moves_offtopic_article_to_general():
    fake_response = MagicMock()
    fake_response.json.return_value = {
        "choices": [{"message": {"content": json.dumps({"0": "โรคระบาด", "1": "ทั่วไป"})}}]
    }
    news = [
        {"title": "Ebola case detected", "desc": "outbreak", "cat": "โรคระบาด"},
        {"title": "$10m on line at inaugural Ultimate Championship", "desc": "sport", "cat": "โรคระบาด"},
    ]
    with patch("news_digest.requests.post", return_value=fake_response):
        result = news_digest.reclassify_categories(news)
    assert result[0]["cat"] == "โรคระบาด"
    assert result[1]["cat"] == "ทั่วไป"


def test_reclassify_falls_back_on_error():
    news = [{"title": "x", "desc": "y", "cat": "โรคระบาด"}]
    with patch("news_digest.requests.post", side_effect=Exception("boom")):
        result = news_digest.reclassify_categories(news)
    assert result[0]["cat"] == "โรคระบาด"  # ป้ายเดิมไม่เปลี่ยนถ้า Groq ล่ม


if __name__ == "__main__":
    test_proofread_returns_fixed_text()
    test_proofread_falls_back_on_mismatched_length()
    test_proofread_falls_back_on_error()
    test_proofread_skips_when_no_groq_key()
    test_reclassify_moves_offtopic_article_to_general()
    test_reclassify_falls_back_on_error()
    print("OK: proofread_thai + reclassify_categories self-checks passed")
