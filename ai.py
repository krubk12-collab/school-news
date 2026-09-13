"""ตัวกลางเรียก AI หลายค่าย: สลับค่ายเมื่อล่ม/ตอบผิดรูป, ยิงซ้ำเมื่อคำตอบถูกตัด, นับโทเค็น+ค่าใช้จ่าย"""
import json
import os
import threading
import time
from datetime import datetime, timezone

import requests

PROVIDERS = {
    # deepseek-flash เปิดโหมดคิดเป็นค่าเริ่มต้น: โทเค็นคิดกินงบ max_tokens จนคำตอบถูกตัด + แพงขึ้น 3-4 เท่า
    # (วัดจริง 13 ก.ย. 69: 14/16 ครั้งถูกตัด) ชื่อเก่า deepseek-chat เคยเป็นแบบไม่คิด แต่ไม่อยู่ในเอกสารแล้ว
    "deepseek": {"url": "https://api.deepseek.com/v1/chat/completions", "model": "deepseek-flash",
                 "key_env": "DEEPSEEK_API_KEY", "extra": {"thinking": {"type": "disabled"}}},
    # ต้องปิดโหมดคิด ไม่งั้นโทเค็นที่ใช้คิดกินงบ max_tokens จนคำตอบขาด (ทดสอบแล้ว 13 ก.ย. 69)
    "gemini": {"url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
               "model": "gemini-flash-latest", "key_env": "GEMINI_API_KEY", "extra": {"reasoning_effort": "none"}},
    # ฟรีแต่จำกัด 8,000 โทเค็น/นาที — เหมาะกับงานสั้น ถ้าเป็นตัวสำรองของงานยาวอาจโดนปฏิเสธ
    "groq": {"url": "https://api.groq.com/openai/v1/chat/completions", "model": "qwen/qwen3.8-27b",
             "key_env": "GROQ_API_KEY", "extra": {}},
}
MAX_TOKENS_CAP = 16000

# ราคา deepseek-flash ต่อ 1M โทเค็น (USD) ช่วงปกติ จาก api-docs.deepseek.com/quick_start/pricing ณ 13 ก.ย. 69
# ช่วงลดราคาเหลือครึ่งหนึ่ง; คิดแบบไม่มี cache hit (ประเมินเผื่อสูงไว้)
DEEPSEEK_PEAK_PRICE = {"input": 0.3, "output": 1.2}

USAGE = []
_lock = threading.Lock()


def _log(rec):
    with _lock:
        USAGE.append(rec)


def _is_peak(dt):
    """ช่วงราคาเต็มของ DeepSeek: 01-04 และ 06-10 UTC วันจันทร์-ศุกร์"""
    return dt.weekday() < 5 and (1 <= dt.hour < 4 or 6 <= dt.hour < 10)


def chat_json(prompt, max_tokens, validate=None, providers=("deepseek", "gemini", "groq"), temperature=0.7, label=""):
    """คืน (dict ที่ผ่านการตรวจ, ชื่อค่าย) หรือ (None, None) ถ้าทุกค่ายล้มเหลว
    validate(dict) -> None ถ้าผ่าน หรือข้อความบอกปัญหา (จะข้ามไปค่ายถัดไป)"""
    for name in providers:
        p = PROVIDERS[name]
        key = os.environ.get(p["key_env"])
        if not key:
            continue
        tokens = max_tokens
        for attempt in (1, 2):
            rec = {"label": label, "provider": name, "model": p["model"], "attempt": attempt, "ok": False,
                   "prompt_tokens": 0, "completion_tokens": 0}
            body = {"model": p["model"], "messages": [{"role": "user", "content": prompt}],
                    "temperature": temperature, "max_tokens": tokens,
                    "response_format": {"type": "json_object"}, **p["extra"]}
            t0 = time.time()
            try:
                r = requests.post(p["url"], json=body, timeout=120,
                                  headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
                rec["sec"] = round(time.time() - t0, 1)
                j = r.json()
                u = j.get("usage") or {}
                rec["prompt_tokens"] = u.get("prompt_tokens") or 0
                rec["completion_tokens"] = u.get("completion_tokens") or 0
                if r.status_code != 200:
                    raise ValueError(f"http {r.status_code}: {str(j)[:120]}")
                choice = j["choices"][0]
                if choice.get("finish_reason") == "length":
                    if attempt == 1 and tokens < MAX_TOKENS_CAP:
                        rec["error"] = f"cut off at {tokens} tokens, retrying"
                        _log(rec)
                        tokens = min(MAX_TOKENS_CAP, tokens * 2)
                        continue
                    raise ValueError(f"cut off at {tokens} tokens")
                parsed = json.loads(choice["message"]["content"])
                problem = validate(parsed) if validate else None
                if problem:
                    raise ValueError(f"invalid: {problem}")
                rec["ok"] = True
                _log(rec)
                return parsed, name
            except Exception as e:
                rec.setdefault("sec", round(time.time() - t0, 1))
                rec["error"] = str(e)[:200]
                _log(rec)
                break
    return None, None


def usage_summary(now=None):
    now = now or datetime.now(timezone.utc)
    by = {}
    for rec in USAGE:
        b = by.setdefault(rec["provider"], {"calls": 0, "failed": 0, "prompt_tokens": 0, "completion_tokens": 0})
        b["calls"] += 1
        b["failed"] += 0 if rec["ok"] else 1
        b["prompt_tokens"] += rec["prompt_tokens"]
        b["completion_tokens"] += rec["completion_tokens"]
    ds = by.get("deepseek", {"prompt_tokens": 0, "completion_tokens": 0})
    factor = 1 if _is_peak(now) else 0.5
    cost = (ds["prompt_tokens"] * DEEPSEEK_PEAK_PRICE["input"] + ds["completion_tokens"] * DEEPSEEK_PEAK_PRICE["output"]) / 1e6 * factor
    return {"calls": len(USAGE), "failed_calls": sum(1 for r in USAGE if not r["ok"]),
            "by_provider": by, "deepseek_cost_usd": round(cost, 5), "peak_price": factor == 1,
            "fallbacks": sorted({r["label"] for r in USAGE if r["ok"] and r["provider"] != "deepseek" and r["label"] != "reclassify"})}
