import requests
import json
import time
import os
from tqdm import tqdm
from collections import Counter
import numpy as np

# =========================
# 1. 核心配置与个人简介
# =========================
USERNAME = "905494"
TOKEN = "3ARCQX8efLOL3M8vRhYOIDETaauJZtEE6n34F5OD"

BIO = """欢迎来加好友)
我也没啥阅历，瞎看番的，一个入坑晚的小登
----------------------------------------------------------------------
评分自己主观感受为重，大部分是自己的情感表达，所以感叹句子比较多
我自己看的开心舒服就是高分
不懂什么分镜节奏之类的，也全靠自己的感觉
就算剧情节奏小崩之类的，没影响我观感就行
厨力 大于 有趣 大于 剧情 大于 制作
情绪价值和给我留下的印象很重要
----------------------------------------------------------------------
(主观角度)
4分基本就是到偏差的了
5分差不多厕纸
6分是一般，或者说是能看的厕纸级别的
7分，认为不错的番，能让我产生好感的
8分，给我惊喜的，确实有意思的
9分的基本厨力和喜爱度占了一半程度
10分基本就是我主观上的认为的神作
----------------------------------------------------------------------
看番基本是追当季度番，外加补一部以前的番
不太喜欢看日常类的，感觉有点乏味，也不太喜欢需要对电波的，也不太想看画风特别老的动漫，机甲类型的也不太感冒，其他的除了特别恶心的bl都接受，也都愿意看
----------------------------------------------------------------------
问我给的评分为什么这么高？
小登补番肯定看自己喜欢的啊，给分不就高了吗(ง •_•)ง"""

SUBJECT_TYPE = 2
LIMIT = 50

base_path = os.path.dirname(os.path.abspath(__file__))
SAVE_JSON = os.path.join(base_path, "bangumi_data.json")
TEMP_FILE = os.path.join(base_path, "bangumi_temp.json")

STOP_TAGS = {"日本", "动画", "TV", "OVA", "系列"}

session = requests.Session()
headers = {"User-Agent": f"BangumiAIEngine/Final (User:{USERNAME})"}
if TOKEN:
    headers["Authorization"] = f"Bearer {TOKEN}"
session.headers.update(headers)

# =========================
# 2. 请求与精简逻辑
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

def get_score(sid):
    data = fetch(f"https://api.bgm.tv/v0/subjects/{sid}")
    return data.get("rating", {}).get("score", 0) if data else 0

def slim(item):
    subject = item.get("subject", {})
    sid = subject.get("id")
    if not sid:
        return None

    raw_tags = [t.get("name") for t in subject.get("tags", []) if isinstance(t, dict)]
    tags = [t for t in raw_tags if t not in STOP_TAGS][:10]
    
    print(f" 🔍 同步数据: {subject.get('name_cn') or subject.get('name')}")

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
# 3. 抓取数据
# =========================
if os.path.exists(TEMP_FILE):
    os.remove(TEMP_FILE)

OFFSET = 0
all_data_map = {}

probe = fetch(f"https://api.bgm.tv/v0/users/{USERNAME}/collections?limit=1&subject_type={SUBJECT_TYPE}")
if not probe: exit("❌ 无法连接到 API")
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
# 4. 🧠 AI画像计算
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
# 5. 🎯 推荐接口
# =========================
high_score = [d for d in watched if d["my_rate"] >= 8]
low_score = [d for d in watched if d["my_rate"] <= 5]

recommendation_hint = {
    "high_score_examples": [d["name_cn"] for d in high_score[:10]],
    "low_score_examples": [d["name_cn"] for d in low_score[:10]],
    "preferred_tags": [t for t, _ in Counter(t for d in high_score for t in d["tags"]).most_common(5)],
    "avoid_tags": [t for t, _ in Counter(t for d in low_score for t in d["tags"]).most_common(5)],
    "summary": f"偏好 {'/'.join(top_tags)}"
}

# =========================
# 6. 最终输出
# =========================
output = {
    # 结合了你的用户名和BIO
    "user_info": {"username": USERNAME, "bio": BIO},
    "collections": collections,
    "ai_profile": ai_profile,
    "recommendation_hint": recommendation_hint
}

with open(SAVE_JSON, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

if os.path.exists(TEMP_FILE):
    os.remove(TEMP_FILE)

print("\n🎉 完成！已生成带有 AI画像 和 个人简介 的全新数据文件。")
