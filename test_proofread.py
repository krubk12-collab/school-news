import json
import os
from unittest.mock import patch, MagicMock

os.environ.setdefault("DEEPSEEK_API_KEY", "dummy")
os.environ.setdefault("NEWSAPI_KEY", "dummy")
import news_digest


def test_proofread_returns_fixed_text():
    fake_response = MagicMock()
    fake_response.json.return_value = {
        "choices": [{"message": {"content": json.dumps({"analysis": "แก้แล้ว", "summaries": ["ก", "ข"]})}}]
    }
    with patch("news_digest.requests.post", return_value=fake_response):
        analysis, summaries = news_digest.proofread_thai("ผิด", ["a", "b"])
    assert analysis == "แก้แล้ว"
    assert summaries == ["ก", "ข"]


def test_proofread_falls_back_on_mismatched_length():
    fake_response = MagicMock()
    fake_response.json.return_value = {
        "choices": [{"message": {"content": json.dumps({"analysis": "แก้แล้ว", "summaries": ["ก"]})}}]
    }
    with patch("news_digest.requests.post", return_value=fake_response):
        analysis, summaries = news_digest.proofread_thai("ผิด", ["a", "b"])
    assert summaries == ["a", "b"]


def test_proofread_falls_back_on_error():
    with patch("news_digest.requests.post", side_effect=Exception("boom")):
        analysis, summaries = news_digest.proofread_thai("ต้นฉบับ", ["a"])
    assert analysis == "ต้นฉบับ"
    assert summaries == ["a"]


if __name__ == "__main__":
    test_proofread_returns_fixed_text()
    test_proofread_falls_back_on_mismatched_length()
    test_proofread_falls_back_on_error()
    print("OK: proofread_thai self-checks passed")
