import requests
import json
import sys
import os
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import zoneinfo

import ai

NEWSAPI_KEY = os.environ["NEWSAPI_KEY"]
TRUSTED_DOMAINS = "reuters.com,apnews.com,bbc.com,aljazeera.com,theguardian.com,cnn.com,npr.org"

DISEASE_QUERIES = [
    "disease outbreak",
    "virus outbreak",
    "pandemic",
    "infectious disease",
    "epidemic",
]
DISEASE_EXCLUDE = ' NOT (malware OR ransomware OR cyberattack OR hacking OR "computer virus" OR antivirus OR software)'

AI_QUERIES = ["artificial intelligence", "generative AI OR large language model"]
WAR_QUERIES = ["Ukraine Russia war", "Israel Gaza conflict", "armed conflict OR military strike"]
DISASTER_QUERIES = ["earthquake disaster", "flood disaster", "wildfire OR hurricane OR typhoon"]

CATEGORY_ICONS = {
    "โรคระบาด": "🦠",
    "สงคราม": "⚔️",
    "ภัยพิบัติ": "🚨",
    "เทคโนโลยี AI": "🤖",
    "สุขภาพ": "🩺",
    "วิทยาศาสตร์": "🔬",
    "เทคโนโลยี": "💻",
    "ทั่วไป": "📰"
}
ORDERED_CATEGORIES = ["โรคระบาด", "สงคราม", "ภัยพิบัติ", "เทคโนโลยี AI", "สุขภาพ", "วิทยาศาสตร์", "เทคโนโลยี", "ทั่วไป"]

def get_news():
    news = []
    try:
        categories = ["health", "science", "technology", "general"]
        cat_map = {
            "health": "สุขภาพ",
            "science": "วิทยาศาสตร์",
            "technology": "เทคโนโลยี",
            "general": "ทั่วไป"
        }
        for cat in categories:
            try:
                base_url = "https://newsapi.org/v2/top-headlines"
                params = {
                    "category": cat,
                    "language": "en",
                    "pageSize": 5,
                    "apiKey": NEWSAPI_KEY
                }
                r = requests.get(base_url, params=params, timeout=10)
                if r.json().get('status') == 'ok':
                    for a in r.json().get('articles', []):
                        news.append({
                            "title": a.get('title', ''),
                            "desc": a.get('description', ''),
                            "source": a.get('source', {}).get('name', ''),
                            "url": a.get('url', ''),
                            "cat": cat_map[cat]
                        })
            except: pass

        base_everything_url = "https://newsapi.org/v2/everything"
        for q in DISEASE_QUERIES:
            try:
                params = {
                    "q": q + DISEASE_EXCLUDE,
                    "domains": TRUSTED_DOMAINS,
                    "language": "en",
                    "pageSize": 3,
                    "sortBy": "publishedAt",
                    "apiKey": NEWSAPI_KEY
                }
                r = requests.get(base_everything_url, params=params, timeout=10)
                if r.json().get('status') == 'ok':
                    for a in r.json().get('articles', []):
                        news.append({
                            "title": a.get('title', ''),
                            "desc": a.get('description', ''),
                            "source": a.get('source', {}).get('name', ''),
                            "url": a.get('url', ''),
                            "cat": "โรคระบาด"
                        })
            except: pass

        for q in AI_QUERIES:
            try:
                params = {
                    "q": q,
                    "domains": TRUSTED_DOMAINS,
                    "language": "en",
                    "pageSize": 4,
                    "sortBy": "publishedAt",
                    "apiKey": NEWSAPI_KEY
                }
                r = requests.get(base_everything_url, params=params, timeout=10)
                if r.json().get('status') == 'ok':
                    for a in r.json().get('articles', []):
                        news.append({
                            "title": a.get('title', ''),
                            "desc": a.get('description', ''),
                            "source": a.get('source', {}).get('name', ''),
                            "url": a.get('url', ''),
                            "cat": "เทคโนโลยี AI"
                        })
            except: pass

        for q in WAR_QUERIES:
            try:
                params = {
                    "q": q,
                    "domains": TRUSTED_DOMAINS,
                    "language": "en",
                    "pageSize": 3,
                    "sortBy": "publishedAt",
                    "apiKey": NEWSAPI_KEY
                }
                r = requests.get(base_everything_url, params=params, timeout=10)
                if r.json().get('status') == 'ok':
                    for a in r.json().get('articles', []):
                        news.append({
                            "title": a.get('title', ''),
                            "desc": a.get('description', ''),
                            "source": a.get('source', {}).get('name', ''),
                            "url": a.get('url', ''),
                            "cat": "สงคราม"
                        })
            except: pass

        for q in DISASTER_QUERIES:
            try:
                params = {
                    "q": q,
                    "domains": TRUSTED_DOMAINS,
                    "language": "en",
                    "pageSize": 3,
                    "sortBy": "publishedAt",
                    "apiKey": NEWSAPI_KEY
                }
                r = requests.get(base_everything_url, params=params, timeout=10)
                if r.json().get('status') == 'ok':
                    for a in r.json().get('articles', []):
                        news.append({
                            "title": a.get('title', ''),
                            "desc": a.get('description', ''),
                            "source": a.get('source', {}).get('name', ''),
                            "url": a.get('url', ''),
                            "cat": "ภัยพิบัติ"
                        })
            except: pass

    except Exception as e:
        print(f"Error in get_news: {e}", file=sys.stderr)

    return news

def dedupe_news(news):
    """ตัดข่าวซ้ำ (URL เดียวกัน หรือหัวข้อเดียวกันหลังตัดชื่อสำนักข่าวท้ายหัวข้อ) — เก็บตัวแรกที่เจอ"""
    seen, out = set(), []
    for n in news:
        title = re.sub(r"\s+[-|]\s+[^-|]+$", "", n.get("title") or "").strip().lower()
        keys = {(n.get("url") or "").strip().lower(), title} - {""}
        if keys & seen:
            continue
        seen |= keys
        out.append(n)
    return out

def group_by_category(news):
    grouped = {}
    for n in news:
        cat = n.get("cat")
        if cat not in grouped:
            grouped[cat] = []
        grouped[cat].append(n)
    return grouped

def reclassify_categories(news):
    """เช็คหมวดหมู่ข่าวจริงด้วย AI แทนป้ายที่ติดตอนดึงจาก NewsAPI
    (ป้ายเดิมเดาจาก 'query ไหนดึงมันมา' ไม่ได้เช็คเนื้อหาจริง ทำให้ข่าวกีฬา/บันเทิงหลุดเข้าหมวดเฉพาะทางได้)"""
    if not news:
        return news

    categories = list(CATEGORY_ICONS.keys())
    lines = []
    for i, n in enumerate(news):
        title = (n.get('title') or '').replace('\n', ' ')
        desc = (n.get('desc') or '').replace('\n', ' ')
        lines.append(f"{i}: {title} — {desc}")
    articles_block = "\n".join(lines)

    prompt = (
        "ต่อไปนี้คือหัวข้อข่าวภาษาอังกฤษพร้อมคำโปรย มีดัชนีกำกับแต่ละข่าว "
        f"ให้จัดหมวดหมู่แต่ละข่าวตามเนื้อหาจริง เลือกได้เฉพาะจาก 8 หมวดนี้เท่านั้น: {', '.join(categories)}\n"
        "ถ้าข่าวไม่เข้าข่ายหมวดเฉพาะทางใดเลย (เช่น กีฬา บันเทิง ไลฟ์สไตล์ คดีอาชญากรรมทั่วไป) ให้จัดเป็น \"ทั่วไป\"\n"
        "ตอบกลับเป็น JSON เท่านั้น รูปแบบ {\"0\": \"ชื่อหมวด\", \"1\": \"ชื่อหมวด\", ...} "
        f"ต้องมีครบทุกดัชนีตั้งแต่ 0 ถึง {len(news) - 1}\n\nรายการข่าว:\n{articles_block}"
    )
    # งานสั้น ใช้ Groq ที่ฟรีและเร็วก่อน พลาดค่อยใช้ค่ายอื่น พลาดหมดก็ใช้ป้ายเดิมจาก NewsAPI
    mapping, _ = ai.chat_json(prompt, max_tokens=4000, temperature=0, label="reclassify",
                              providers=("groq", "gemini", "deepseek"),
                              validate=lambda m: None if isinstance(m, dict) else "not an object")
    for i, n in enumerate(news):
        cat = (mapping or {}).get(str(i))
        if cat in categories:
            n["cat"] = cat
    return news

def category_validator(n):
    """คำตอบต้องมีบทวิเคราะห์จริง และสรุป/รายละเอียดครบเท่าจำนวนข่าว ห้ามมีช่องว่าง"""
    def check(p):
        if not isinstance(p.get("analysis"), str) or len(p["analysis"].strip()) < 50:
            return "analysis missing or too short"
        for k in ("summaries", "details"):
            v = p.get(k)
            if not isinstance(v, list) or len(v) != n:
                return f"{k}: got {len(v) if isinstance(v, list) else 'none'}, want {n}"
            if any(not isinstance(x, str) or not x.strip() for x in v):
                return f"{k}: empty item"
        return None
    return check

def analyze_category(category_name, articles):
    """คืน {"analysis", "summaries", "details"} หรือ None ถ้าทุกค่ายล้มเหลว"""
    articles_text = ""
    for i, a in enumerate(articles, 1):
        title = a.get('title') or ''
        desc = a.get('desc') or ''
        source = a.get('source') or ''
        articles_text += f"{i}. {title}\nรายละเอียด: {desc}\nแหล่งข่าว: {source}\n\n"

    if category_name == "โรคระบาด":
        role = "คุณเป็นนักระบาดวิทยา"
        task = "ตอบ: 1)โรคที่น่ากังวลที่สุด 2)แนวโน้ม 3)ผลกระทบไทย 4)คำแนะนำ ตอบภาษาไทย"
        base_tokens = 1800
    elif category_name == "เทคโนโลยี AI":
        role = "คุณเป็นนักวิเคราะห์เทคโนโลยี"
        task = "ตอบภาษาไทย 3 หัวข้อ:\n1) พัฒนาการ/เทคโนโลยีที่น่าจับตาที่สุด\n2) ผลกระทบต่อการทำงาน/การศึกษา/ชีวิตประจำวัน\n3) ความเสี่ยงหรือข้อควรระวัง"
        base_tokens = 1000
    elif category_name == "สงคราม":
        role = "คุณเป็นนักวิเคราะห์ภูมิรัฐศาสตร์"
        task = "ตอบภาษาไทย 3 หัวข้อ:\n1) สถานการณ์ล่าสุดที่สำคัญที่สุด\n2) แนวโน้ม\n3) ผลกระทบต่อเศรษฐกิจโลกหรือไทย"
        base_tokens = 1200
    elif category_name == "ภัยพิบัติ":
        role = "คุณเป็นผู้เชี่ยวชาญภัยพิบัติ"
        task = "ตอบภาษาไทย 3 หัวข้อ:\n1) ความรุนแรง/พื้นที่ที่ได้รับผลกระทบมากที่สุด\n2) แนวโน้มความเสี่ยงที่ต้องจับตา\n3) บทเรียนหรือข้อเตือนภัยสำหรับไทย"
        base_tokens = 1000
    else:
        role = "คุณเป็นนักวิเคราะห์ข่าวทั่วไป"
        task = "ตอบภาษาไทยตาม 3 หัวข้อดังนี้:\n1) ประเด็นสำคัญที่สุด\n2) เรื่องที่น่าสนใจ/น่าติดตาม\n3) ผลกระทบหรือประโยชน์ต่อคนไทย"
        base_tokens = 1000

    # ปรับตามจำนวนข่าวจริง (details ยาวต่อข่าว) — ถ้ายังถูกตัด ai.chat_json จะยิงซ้ำด้วยงบสองเท่าเอง
    max_tokens = min(6000, base_tokens + len(articles) * 250)

    prompt = (
        f"{role} วิเคราะห์ข่าวต่อไปนี้ (หมวด {category_name}):\n{articles_text}\n"
        f"{task}\n\n"
        f"ในส่วนบทวิเคราะห์ ต้องกล่าวถึงทุกประเด็น/เหตุการณ์ที่ปรากฏในข่าวด้านบนอย่างน้อยหนึ่งครั้ง "
        f"อนุญาตให้รวมข่าวที่รายงานเรื่องเดียวกันจากหลายสำนักไว้เป็นประเด็นเดียวได้ แต่ห้ามละเว้นเหตุการณ์ใดไปทั้งหมด\n\n"
        f"นอกจากนี้ สำหรับข่าวแต่ละข้อ (ตามลำดับข้อ 1 ถึง {len(articles)} ด้านบน) ให้เขียน 2 อย่าง:\n"
        f"1. สรุปสั้น (summaries) ภาษาไทยกระชับ ไม่เกิน 15 คำ อ่านแล้วเข้าใจทันที\n"
        f"2. รายละเอียด (details) ภาษาไทย 2-4 ประโยค (ประมาณ 40-70 คำ) ขยายความจากคำโปรยข่าวให้อ่านเข้าใจครบถ้วนโดยไม่ต้องกดออกไปอ่านต้นฉบับ "
        f"ครอบคลุม ใคร/เกิดอะไร/ที่ไหน/ผลกระทบ เท่าที่ข้อมูลที่ให้มามี ห้ามเดาข้อมูลที่ไม่มีในคำโปรยเพิ่มเอง\n\n"
        f"ทั้ง summaries และ details ต้องไม่ใช่แปลตรงตัวจากหัวข้อภาษาอังกฤษ และใช้คำศัพท์ไทยที่ถูกต้องและเป็นที่รู้จักทั่วไปสำหรับของ/แนวคิดต่างประเทศ "
        f"(เช่น bouncy castle = บ้านลม หรือ ปราสาทลม ไม่ใช่คำที่ประดิษฐ์ขึ้นเองอย่าง 'บ่อลม') หากไม่แน่ใจศัพท์เฉพาะ ให้บรรยายสั้นๆ ดีกว่าเดาคำผิด\n\n"
        f"ตอบกลับเป็น JSON เท่านั้น ห้ามมีข้อความอื่นนอก JSON รูปแบบนี้เป๊ะๆ:\n"
        f'{{"analysis": "เนื้อหาวิเคราะห์ตามหัวข้อข้างต้นทั้งหมด", "summaries": ["สรุปข่าวข้อ 1", ...], "details": ["รายละเอียดข่าวข้อ 1", ...]}}\n'
        f"summaries และ details ต้องมีจำนวนสมาชิกเท่ากับจำนวนข่าวพอดี ({len(articles)} ข้อ) เรียงลำดับตรงกับข่าวด้านบนทั้งคู่"
    )

    parsed, _ = ai.chat_json(prompt, max_tokens=max_tokens, validate=category_validator(len(articles)), label=category_name)
    return parsed

def build_category(cat_name, articles, result):
    """result=None (AI ล้มเหลวทุกค่าย) → โชว์แค่ข่าว ไม่มีบทวิเคราะห์ ไม่เอาข้อความ error ขึ้นเว็บ"""
    result = result or {}
    summaries = result.get("summaries") or []
    details = result.get("details") or []
    items = []
    for i, art in enumerate(articles):
        items.append({
            "title": art.get('title', ''),
            "summary_th": summaries[i] if i < len(summaries) else None,
            "detail_th": details[i] if i < len(details) else None,
            "source": art.get('source', ''),
            "url": art.get('url', '')
        })
    return {
        "name": cat_name,
        "icon": CATEGORY_ICONS.get(cat_name, "📰"),
        "count": len(articles),
        "analysis": result.get("analysis", ""),
        "items": items
    }

def main():
    print("="*50)
    print("ระบบรายงานข่าวและวิเคราะห์เชิงลึก (AI-Powered Daily Report)")
    print("="*50)

    if not os.environ.get("DEEPSEEK_API_KEY"):
        print("⚠️ ไม่มี DEEPSEEK_API_KEY", file=sys.stderr)
        sys.exit(1)

    print("กำลังดึงข้อมูลข่าวจาก NewsAPI...")
    raw_news = get_news()

    if not raw_news:
        print("\n⚠️ ไม่สามารถดึงข่าวปัจจุบันได้ หรือไม่มีข่าวใหม่ (NewsAPI quota หมด?) — คงข่าวเดิมบนเว็บไว้", file=sys.stderr)
        sys.exit(1)

    news = dedupe_news(raw_news)
    print(f"ดึงข่าวได้ {len(raw_news)} ข่าว ตัดซ้ำเหลือ {len(news)} ข่าว")

    print("กำลังตรวจสอบ/จัดหมวดหมู่ข่าวใหม่...")
    news = reclassify_categories(news)
    grouped = group_by_category(news)

    cats = [c for c in ORDERED_CATEGORIES if grouped.get(c)]
    if not cats:
        print("\n⚠️ ไม่มีข่าวในหมวดหมู่ที่ต้องการ", file=sys.stderr)
        sys.exit(1)

    print(f"กำลังวิเคราะห์ {len(cats)} หมวดพร้อมกัน...")
    with ThreadPoolExecutor(max_workers=len(cats)) as pool:
        results = list(pool.map(lambda c: analyze_category(c, grouped[c]), cats))

    usage = ai.usage_summary()
    failed = [c for c, r in zip(cats, results) if r is None]
    print(f"การเรียก AI: {json.dumps(usage, ensure_ascii=False)}")
    if failed:
        print(f"⚠️ หมวดที่ AI ล้มเหลวทุกค่าย (โชว์แค่ข่าว): {', '.join(failed)}", file=sys.stderr)
    if len(failed) == len(cats):
        print("⚠️ ล้มเหลวทุกหมวด — ไม่เขียนทับข่าวเดิมบนเว็บ", file=sys.stderr)
        sys.exit(1)

    categories_list = [build_category(c, grouped[c], r) for c, r in zip(cats, results)]

    tz = zoneinfo.ZoneInfo("Asia/Bangkok")
    now = datetime.now(tz)
    date_str = f"{now.year + 543:04d}-{now.month:02d}-{now.day:02d}"
    output_data = {
        "date": date_str,
        "generated_at": now.isoformat(),
        "categories": categories_list
    }

    os.makedirs("data", exist_ok=True)
    try:
        for path in (f"data/{date_str}.json", "data/latest.json"):
            with open(path, "w", encoding="utf-8") as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            print(f"บันทึกไฟล์สำเร็จ: {path}")
        with open("data/usage.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps({"generated_at": now.isoformat(), "articles_raw": len(raw_news),
                                "articles": len(news), "failed_categories": failed, **usage}, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการบันทึกไฟล์: {e}", file=sys.stderr)
        sys.exit(1)

    print("การดำเนินการทั้งหมดเสร็จสิ้นอย่างสมบูรณ์!")

if __name__ == "__main__":
    main()
