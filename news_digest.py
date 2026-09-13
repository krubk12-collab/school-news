import requests
import json
import sys
import os
import re
from datetime import datetime
import zoneinfo

# Read API keys from environment variables
API_KEY = os.environ["DEEPSEEK_API_KEY"]
NEWSAPI_KEY = os.environ["NEWSAPI_KEY"]

DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
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

def group_by_category(news):
    grouped = {}
    for n in news:
        cat = n.get("cat")
        if cat not in grouped:
            grouped[cat] = []
        grouped[cat].append(n)
    return grouped

def classify_disease_type(articles):
    cats = {
        "ไวรัสทางเดินหายใจ": ["COVID", "flu", "H5N1", "H10N3", "respiratory", "influenza"],
        "ไวรัสเลือดออก": ["Dengue", "Marburg", "Ebola", "hemorrhagic"],
        "ไวรัสระบบประสาท": ["Nipah", "encephalitis", "Japanese"],
        "โรคติดต่อผิวหนัง": ["Mpox", "Monkeypox"],
        "เชื้อดื้อยา": ["Antimicrobial", "AMR", "antibiotic"],
        "โรคระบาดทั่วไป": ["outbreak", "pandemic", "epidemic"]
    }
    result = {k: [] for k in cats}
    result["อื่นๆ"] = []
    for n in articles:
        title = n.get('title') or ''
        desc = n.get('desc') or ''
        t = (title + desc).lower()
        assigned = False
        for cat, kws in cats.items():
            for kw in kws:
                if kw.lower() in t:
                    result[cat].append(n)
                    assigned = True
                    break
            if assigned: break
        if not assigned:
            result["อื่นๆ"].append(n)
    return result

def ask_deepseek_category(category_name, articles):
    articles_text = ""
    for i, a in enumerate(articles, 1):
        title = a.get('title') or ''
        desc = a.get('desc') or ''
        source = a.get('source') or ''
        articles_text += f"{i}. {title}\nรายละเอียด: {desc}\nแหล่งข่าว: {source}\n\n"

    if category_name == "โรคระบาด":
        role = "คุณเป็นนักระบาดวิทยา"
        task = "ตอบ: 1)โรคที่น่ากังวลที่สุด 2)แนวโน้ม 3)ผลกระทบไทย 4)คำแนะนำ ตอบภาษาไทย"
        max_tokens = 1800
    elif category_name == "เทคโนโลยี AI":
        role = "คุณเป็นนักวิเคราะห์เทคโนโลยี"
        task = "ตอบภาษาไทย 3 หัวข้อ:\n1) พัฒนาการ/เทคโนโลยีที่น่าจับตาที่สุด\n2) ผลกระทบต่อการทำงาน/การศึกษา/ชีวิตประจำวัน\n3) ความเสี่ยงหรือข้อควรระวัง"
        max_tokens = 1000
    elif category_name == "สงคราม":
        role = "คุณเป็นนักวิเคราะห์ภูมิรัฐศาสตร์"
        task = "ตอบภาษาไทย 3 หัวข้อ:\n1) สถานการณ์ล่าสุดที่สำคัญที่สุด\n2) แนวโน้ม\n3) ผลกระทบต่อเศรษฐกิจโลกหรือไทย"
        max_tokens = 1200
    elif category_name == "ภัยพิบัติ":
        role = "คุณเป็นผู้เชี่ยวชาญภัยพิบัติ"
        task = "ตอบภาษาไทย 3 หัวข้อ:\n1) ความรุนแรง/พื้นที่ที่ได้รับผลกระทบมากที่สุด\n2) แนวโน้มความเสี่ยงที่ต้องจับตา\n3) บทเรียนหรือข้อเตือนภัยสำหรับไทย"
        max_tokens = 1000
    else:
        role = "คุณเป็นนักวิเคราะห์ข่าวทั่วไป"
        task = "ตอบภาษาไทยตาม 3 หัวข้อดังนี้:\n1) ประเด็นสำคัญที่สุด\n2) เรื่องที่น่าสนใจ/น่าติดตาม\n3) ผลกระทบหรือประโยชน์ต่อคนไทย"
        max_tokens = 1000

    prompt = (
        f"{role} วิเคราะห์ข่าวต่อไปนี้ (หมวด {category_name}):\n{articles_text}\n"
        f"{task}\n\n"
        f"นอกจากนี้ ให้สรุปข่าวแต่ละข้อ (ตามลำดับข้อ 1 ถึง {len(articles)} ด้านบน) เป็นภาษาไทยสั้นกระชับ "
        f"ไม่เกิน 15 คำต่อข้อ อ่านแล้วเข้าใจทันที ไม่ใช่แปลตรงตัวจากหัวข้อภาษาอังกฤษ\n\n"
        f"ตอบกลับเป็น JSON เท่านั้น ห้ามมีข้อความอื่นนอก JSON รูปแบบนี้เป๊ะๆ:\n"
        f'{{"analysis": "เนื้อหาวิเคราะห์ตามหัวข้อข้างต้นทั้งหมด", "summaries": ["สรุปข่าวข้อ 1", "สรุปข่าวข้อ 2", ...]}}\n'
        f"summaries ต้องมีจำนวนสมาชิกเท่ากับจำนวนข่าวพอดี ({len(articles)} ข้อ) เรียงลำดับตรงกับข่าวด้านบน"
    )

    try:
        r = requests.post(
            DEEPSEEK_URL,
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": max_tokens,
                "response_format": {"type": "json_object"}
            },
            timeout=45
        )
        raw = r.json()['choices'][0]['message']['content']
        parsed = json.loads(raw)
        analysis = parsed.get("analysis") or ""
        summaries = parsed.get("summaries") or []
        if not isinstance(summaries, list):
            summaries = []
        return {"analysis": analysis, "summaries": [str(s) for s in summaries]}
    except Exception as e:
        return {"analysis": f"เกิดข้อผิดพลาดในการวิเคราะห์ด้วย AI: {str(e)}", "summaries": []}

def proofread_thai(analysis, summaries):
    """ตรวจตัวสะกด/วรรณยุกต์/ไวยากรณ์ไทยอีกรอบก่อนเผยแพร่ขึ้นเว็บ (ไม่แก้เนื้อหา)"""
    payload = {"analysis": analysis, "summaries": summaries}
    prompt = (
        "ตรวจและแก้ตัวสะกด วรรณยุกต์ และไวยากรณ์ภาษาไทยใน JSON นี้ให้ถูกต้อง "
        "ห้ามเปลี่ยนเนื้อหา ความหมาย หรือโครงสร้างประโยค แก้เฉพาะจุดที่สะกดผิดเท่านั้น "
        "ตอบกลับเป็น JSON รูปแบบเดิมเป๊ะๆ (คีย์ analysis และ summaries จำนวนสมาชิกเท่าเดิม):\n\n"
        + json.dumps(payload, ensure_ascii=False)
    )
    try:
        r = requests.post(
            DEEPSEEK_URL,
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
                "max_tokens": 2000,
                "response_format": {"type": "json_object"}
            },
            timeout=45
        )
        raw = r.json()['choices'][0]['message']['content']
        parsed = json.loads(raw)
        fixed_analysis = parsed.get("analysis") or analysis
        fixed_summaries = parsed.get("summaries") or summaries
        if not isinstance(fixed_summaries, list) or len(fixed_summaries) != len(summaries):
            fixed_summaries = summaries
        return fixed_analysis, [str(s) for s in fixed_summaries]
    except Exception:
        return analysis, summaries  # พิสูจน์อักษรพลาด ใช้ต้นฉบับแทน ไม่ทำให้ทั้งระบบล่ม

def main():
    print("="*50)
    print("ระบบรายงานข่าวและวิเคราะห์เชิงลึก (AI-Powered Daily Report)")
    print("="*50)
    
    print("กำลังดึงข้อมูลข่าวจาก NewsAPI...")
    news = get_news()
    
    if not news:
        print("\n⚠️ ไม่สามารถดึงข่าวปัจจุบันได้ หรือไม่มีข่าวใหม่", file=sys.stderr)
        sys.exit(1)

    print(f"ดึงข้อมูลข่าวเสร็จสิ้น: ทั้งหมด {len(news)} ข่าว")
    
    # จัดกลุ่มตามหมวดหมู่ภาษาไทย
    grouped = group_by_category(news)
    
    # ส่งข้อความวิเคราะห์รายหมวดด้วย DeepSeek
    categories_list = []
    
    # กำหนดลำดับหมวดหมู่
    ordered_categories = ["โรคระบาด", "สงคราม", "ภัยพิบัติ", "เทคโนโลยี AI", "สุขภาพ", "วิทยาศาสตร์", "เทคโนโลยี", "ทั่วไป"]
    
    for cat_name in ordered_categories:
        if cat_name not in grouped or not grouped[cat_name]:
            continue
            
        articles = grouped[cat_name]
        print(f"กำลังวิเคราะห์หมวด '{cat_name}' ด้วย DeepSeek AI ({len(articles)} ข่าว)...")
        result = ask_deepseek_category(cat_name, articles)
        analysis_text = result.get("analysis", "")
        summaries = result.get("summaries", [])
        analysis_text, summaries = proofread_thai(analysis_text, summaries)

        items_list = []
        for i, art in enumerate(articles):
            summary_th = summaries[i] if i < len(summaries) and summaries[i] else None
            items_list.append({
                "title": art.get('title', ''),
                "summary_th": summary_th,   # สรุปสั้นภาษาไทย จาก DeepSeek — None ถ้า AI ตอบไม่ครบ/parse ไม่ได้
                "source": art.get('source', ''),
                "url": art.get('url', '')
            })

        categories_list.append({
            "name": cat_name,
            "icon": CATEGORY_ICONS.get(cat_name, "📰"),
            "count": len(articles),
            "analysis": analysis_text,
            "items": items_list
        })
        
    if not categories_list:
        print("\n⚠️ ไม่มีข่าวในหมวดหมู่ที่ต้องการ", file=sys.stderr)
        sys.exit(1)
        
    # สร้างโครงสร้าง JSON ตามสเปก
    tz = zoneinfo.ZoneInfo("Asia/Bangkok")
    now = datetime.now(tz)
    
    th_year = now.year + 543
    date_str = f"{th_year:04d}-{now.month:02d}-{now.day:02d}"
    
    output_data = {
        "date": date_str,
        "generated_at": now.isoformat(),
        "categories": categories_list
    }
    
    # เขียนไฟล์ลง data/
    os.makedirs("data", exist_ok=True)
    
    daily_file = f"data/{date_str}.json"
    latest_file = "data/latest.json"
    
    try:
        with open(daily_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        print(f"บันทึกไฟล์รายวันสำเร็จ: {daily_file}")
        
        with open(latest_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        print(f"บันทึกไฟล์ล่าสุดสำเร็จ: {latest_file}")
        
    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการบันทึกไฟล์ JSON: {e}", file=sys.stderr)
        sys.exit(1)
        
    print("การดำเนินการทั้งหมดเสร็จสิ้นอย่างสมบูรณ์!")

if __name__ == "__main__":
    main()
