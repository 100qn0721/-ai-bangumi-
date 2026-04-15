import requests
import json
import time
import os
from tqdm import tqdm
from collections import Counter
import numpy as np

# =========================
# 配置
# =========================
USERNAME = "你的用户名"
TOKEN = ""

SUBJECT_TYPE = 2
LIMIT = 50

base_path = os.path.dirname(os.path.abspath(__file__))
SAVE_JSON = os.path.join(base_path, "bangumi_data.json")
TEMP_FILE = os.path.join(base_path, "bangumi_temp.json")

STOP_TAGS = {"日本", "动画", "TV", "OVA", "系列"}

session = requests.Session()
headers = {"User-Agent": f"BangumiAIEngine/9.0 (User:{USERNAME})"}
if TOKEN:
    headers["Authorization"] = f"Bearer {TOKEN}"
session.headers.update(headers)

# =========================
# 请求函数
# =========================
def fetch(url, retries=5):
    for i in range(retries):
        try:
            r = session.get(url, timeout=12)
            if r.status_code == 200:
                return r.json()
            elif r.status_code == 429:
                time.sleep(10)
        except:
            pass
        time.sleep(2)
    return None

# =========================
# 获取评分
# =========================
def get_score(sid):
    data = fetch(f"https://api.bgm.tv/v0/subjects/{sid}")
    return data.get("rating", {}).get("score", 0) if data else 0

# =========================
# 精简数据
# =========================
def slim(item):
    subject = item.get("subject", {})
    sid = subject.get("id")
    if not sid:
        return None

    raw_tags = [t.get("name") for t in subject.get("tags", []) if isinstance(t, dict)]
    tags = [t for t in raw_tags if t not in STOP_TAGS][:10]

    return {
        "subject_id": sid,
        "name_cn": subject.get("name_cn") or subject.get("name"),
        "year": subject.get("date", "")[:4] if subject.get("date") else "未知",
        "global_score": get_score(sid),
        "status": item.get("type"),
        "my_rate": item.get("rate", 0),
        "my_comment": item.get("comment"),
        "tags": tags,
        "updated_at": item.get("updated_at")
    }

# =========================
# 推荐函数
# =========================
def get_recommendations(top_tags, watched_ids, limit=20):
    results = []

    for tag in top_tags[:3]:
        url = f"https://api.bgm.tv/v0/search/subjects?keyword={tag}&limit=10"
        data = fetch(url)

        if not data or "data" not in data:
            continue

        for item in data["data"]:
            sid = item.get("id")

            if not sid or str(sid) in watched_ids:
                continue

            results.append({
                "name": item.get("name_cn") or item.get("name"),
                "score": item.get("rating", {}).get("score", 0),
                "tag": tag
            })

    results = sorted(results, key=lambda x: x["score"], reverse=True)
    return results[:limit]

# =========================
# 抓取数据
# =========================
if os.path.exists(TEMP_FILE):
    os.remove(TEMP_FILE)

OFFSET = 0
all_data_map = {}

probe = fetch(f"https://api.bgm.tv/v0/users/{USERNAME}/collections?limit=1&subject_type={SUBJECT_TYPE}")
total = probe.get("total", 0)

pbar = tqdm(total=total, desc="🎬 抓取进度")

while OFFSET < total:
    res = fetch(f"https://api.bgm.tv/v0/users/{USERNAME}/collections?limit={LIMIT}&offset={OFFSET}&subject_type={SUBJECT_TYPE}")
    if not res or "data" not in res:
        break

    for item in res["data"]:
        s = slim(item)
        if s:
            all_data_map[str(s["subject_id"])] = s
        pbar.update(1)

    OFFSET += LIMIT

    with open(TEMP_FILE, "w", encoding="utf-8") as f:
        json.dump({"offset": OFFSET}, f)

    time.sleep(0.5)

pbar.close()

collections = list(all_data_map.values())

# =========================
# AI画像
# =========================
watched = [d for d in collections if d["status"] == 2]

scores = [d["my_rate"] for d in watched if d["my_rate"] > 0]
avg_score = sum(scores) / len(scores) if scores else 0
std = np.std(scores) if scores else 0

score_style = "情绪驱动" if std > 2 else "相对理性"

emotion_words = ["神", "爽", "哭", "炸", "喜欢", "无聊", "厕纸"]
emotion_count = sum(
    any(word in (d["my_comment"] or "") for word in emotion_words)
    for d in watched
)
emotion_ratio = emotion_count / len(watched) if watched else 0

bias_list = [
    d["my_rate"] - d["global_score"]
    for d in watched
    if d["my_rate"] > 0 and d["global_score"] > 0
]
avg_bias = sum(bias_list) / len(bias_list) if bias_list else 0

tag_counter = Counter()
for d in watched:
    tag_counter.update(d["tags"])

top_tags = [t for t, _ in tag_counter.most_common(8)]

ai_profile = {
    "avg_score": round(avg_score, 2),
    "score_std": round(std, 2),
    "score_style": score_style,
    "emotion_ratio": round(emotion_ratio, 2),
    "avg_bias": round(avg_bias, 2),
    "favorite_tags": top_tags
}

# =========================
# 推荐
# =========================
watched_ids = set(all_data_map.keys())

recommendations = get_recommendations(top_tags, watched_ids)

# =========================
# 输出
# =========================
output = {
    "user_info": {"username": USERNAME},
    "collections": collections,
    "ai_profile": ai_profile,
    "recommendations": recommendations
}

with open(SAVE_JSON, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

if os.path.exists(TEMP_FILE):
    os.remove(TEMP_FILE)

print("\n🎉 完成！AI+推荐系统已生成")
