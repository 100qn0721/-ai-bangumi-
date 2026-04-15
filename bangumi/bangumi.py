import requests
import json
import time
import os
from tqdm import tqdm

# =========================
# 1. 核心配置
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
STOP_TAGS = {"日本", "动画", "TV", "OVA", "核心", "系列"}

session = requests.Session()
headers = {"User-Agent": f"BangumiVisualEngine/7.1 (User:{USERNAME})"}
if TOKEN: headers["Authorization"] = f"Bearer {TOKEN}"
session.headers.update(headers)

def fetch(url, retries=5):
    for i in range(retries):
        try:
            r = session.get(url, timeout=12)
            if r.status_code == 200: return r.json()
            elif r.status_code == 429: time.sleep(15)
        except: pass
        time.sleep(2)
    return None

def get_subject_score(sid):
    data = fetch(f"https://api.bgm.tv/v0/subjects/{sid}")
    return data.get("rating", {}).get("score", 0) if data else 0

def slim(item):
    subject = item.get("subject", {})
    sid = subject.get("id")
    if not sid: return None
    
    # 删除了排名抓取，大幅提升速度
    global_score = get_subject_score(sid)
    raw_tags = [t.get("name") for t in subject.get("tags", []) if isinstance(t, dict)]
    filtered_tags = [t for t in raw_tags if t not in STOP_TAGS][:10]
    
    return {
        "subject_id": sid,
        "name_cn": subject.get("name_cn") or subject.get("name"),
        "year": subject.get("date", "")[:4] if subject.get("date") else "未知",
        "global_score": global_score,
        "status": item.get("type"), 
        "my_rate": item.get("rate", 0),
        "my_comment": item.get("comment"), 
        "tags": filtered_tags,
        "updated_at": item.get("updated_at")
    }

# --- 数据同步逻辑 ---
# 强制清理旧缓存，确保能抓到更新时间
if os.path.exists(TEMP_FILE): os.remove(TEMP_FILE)
OFFSET, all_data_map = 0, {}

probe_res = fetch(f"https://api.bgm.tv/v0/users/{USERNAME}/collections?limit=1&offset=0&subject_type={SUBJECT_TYPE}")
if not probe_res: exit("❌ API连接失败")

total_count = probe_res.get("total", 0)
pbar = tqdm(total=total_count, desc="🎬 抓取进度")

while OFFSET < total_count:
    res = fetch(f"https://api.bgm.tv/v0/users/{USERNAME}/collections?limit={LIMIT}&offset={OFFSET}&subject_type={SUBJECT_TYPE}")
    if not res or "data" not in res: break
    for item in res["data"]:
        s_item = slim(item)
        if s_item: all_data_map[str(s_item["subject_id"])] = s_item
        pbar.update(1)
    OFFSET += LIMIT
    with open(TEMP_FILE, "w", encoding="utf-8") as f:
        json.dump({"offset": OFFSET, "data_map": all_data_map}, f, ensure_ascii=False)
    time.sleep(0.5)

pbar.close()

# --- 构建最终 JSON ---
final_output = {
    "user_info": {"username": USERNAME, "bio": BIO},
    "collections": list(all_data_map.values())
}

with open(SAVE_JSON, "w", encoding="utf-8") as f:
    json.dump(final_output, f, ensure_ascii=False, indent=2)

if os.path.exists(TEMP_FILE): os.remove(TEMP_FILE)
print(f"\n🎉 成功！新版 JSON 已生成，包含动态时间。")
