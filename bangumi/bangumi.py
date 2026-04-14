import requests
import json
import time
import os
import csv
from collections import Counter
from tqdm import tqdm
import matplotlib.pyplot as plt

# =========================
# 1. 核心配置与隐私解耦（已记忆）
# =========================
USERNAME = "905494" 
TOKEN = "3ARCQX8efLOL3M8vRhYOIDETaauJZtEE6n34F5OD"             

LIMIT = 50
SUBJECT_TYPE = 2  # 2 = 动画

# 文件命名
SAVE_JSON = "bangumi_data.json"
SAVE_CSV = "bangumi_list.csv"
SAVE_CHART = "bangumi_analysis.png"
TEMP_FILE = "bangumi_temp.json"

# 标签去噪：过滤无分析价值的通用标签
STOP_TAGS = {"日本", "动画", "TV", "OVA", "核心", "系列"}

# =========================
# 2. 性能增强：初始化 Session
# =========================
session = requests.Session()
headers = {"User-Agent": f"BangumiVisualEngine/6.1 (User:{USERNAME})"}
if TOKEN:
    headers["Authorization"] = f"Bearer {TOKEN}"
session.headers.update(headers)

def fetch(url, retries=5):
    delay = 1
    for i in range(retries):
        try:
            r = session.get(url, timeout=12)
            if r.status_code == 200: return r.json()
            elif r.status_code == 429: time.sleep(15 * (i + 1))
        except: pass
        time.sleep(delay)
        delay *= 2
    return None

def slim(item):
    subject = item.get("subject", {})
    rating = subject.get("rating", {})
    sid = subject.get("id")
    if not sid: return None
    
    # 抓取评价内容
    my_comment = item.get("comment") 
    
    raw_tags = [t.get("name") for t in subject.get("tags", []) if isinstance(t, dict)]
    filtered_tags = [t for t in raw_tags if t not in STOP_TAGS][:10]
    
    return {
        "subject_id": sid,
        "name_cn": subject.get("name_cn") or subject.get("name"),
        "year": subject.get("date", "")[:4] if subject.get("date") else "未知",
        "global_rank": rating.get("rank", 0) or 99999,
        "global_score": rating.get("score", 0),
        "status": item.get("type"), 
        "my_rate": item.get("rate", 0),
        "my_comment": my_comment, 
        "tags": filtered_tags
    }

# =========================
# 3. 数据同步逻辑
# =========================
if os.path.exists(TEMP_FILE):
    with open(TEMP_FILE, "r", encoding="utf-8") as f:
        state = json.load(f)
        OFFSET, all_data_map = state.get("offset", 0), state.get("data_map", {})
    print(f"🔄 恢复点：Offset {OFFSET}")
else:
    OFFSET, all_data_map = 0, {}

probe_res = fetch(f"https://api.bgm.tv/v0/users/{USERNAME}/collections?limit=1&offset=0&subject_type={SUBJECT_TYPE}")
if not probe_res: exit("❌ 连接失败")

total_count = probe_res.get("total", 0)
pbar = tqdm(total=total_count, desc="🎬 同步进度")
pbar.n = len(all_data_map)
pbar.refresh()

while OFFSET < total_count:
    url = f"https://api.bgm.tv/v0/users/{USERNAME}/collections?limit={LIMIT}&offset={OFFSET}&subject_type={SUBJECT_TYPE}"
    res = fetch(url)
    if not res or "data" not in res: break
    for item in res["data"]:
        s_item = slim(item)
        if s_item: all_data_map[str(s_item["subject_id"])] = s_item
    OFFSET += LIMIT
    pbar.n = min(OFFSET, total_count)
    pbar.refresh()
    with open(TEMP_FILE, "w", encoding="utf-8") as f:
        json.dump({"offset": OFFSET, "data_map": all_data_map}, f, ensure_ascii=False)
    time.sleep(0.5)

pbar.close()
final_list = list(all_data_map.values())
if os.path.exists(TEMP_FILE): os.remove(TEMP_FILE)

# =========================
# 4. 可视化模块
# =========================
def generate_visualizations(data):
    print("📊 正在生成可视化图表...")
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'sans-serif']
    plt.rcParams['axes.unicode_minus'] = False
    
    watched = [d for d in data if d["status"] == 2]
    rated = [d for d in watched if d["my_rate"] > 0]
    
    if not rated:
        print("⚠️ 没有评分数据，跳过绘图。")
        return

    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle(f'Bangumi 用户审美大数据分析 - {USERNAME}', fontsize=20)

    # (1) 评分分布
    my_scores = [d["my_rate"] for d in rated]
    axes[0, 0].hist(my_scores, bins=range(1, 12), align='left', color='#ff9999', edgecolor='white')
    axes[0, 0].set_title('个人评分分布 (1-10分)')
    axes[0, 0].set_xticks(range(1, 11))

    # (2) 年份分布
    years = [int(d["year"]) for d in watched if d["year"].isdigit()]
    year_counts = Counter(years)
    sorted_years = sorted(year_counts.items())
    axes[0, 1].bar([x[0] for x in sorted_years], [x[1] for x in sorted_years], color='#66b3ff')
    axes[0, 1].set_title('看番年份分布')

    # (3) 审美偏差散点图
    global_scores = [d["global_score"] for d in rated if d["global_score"] > 0]
    user_scores = [d["my_rate"] for d in rated if d["global_score"] > 0]
    axes[1, 0].scatter(global_scores, user_scores, alpha=0.5, color='#99ff99')
    axes[1, 0].plot([0, 10], [0, 10], ls="--", c=".3")
    axes[1, 0].set_title('个人与大众评分关联度')

    # (4) 核心标签
    all_tags = []
    for d in watched: all_tags.extend(d["tags"])
    top_tags = Counter(all_tags).most_common(10)
    axes[1, 1].barh([t[0] for t in top_tags][::-1], [t[1] for t in top_tags][::-1], color='#ffcc99')
    axes[1, 1].set_title('核心审美标签 Top 10')

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.savefig(SAVE_CHART)
    print(f"✅ 图表已保存至: {SAVE_CHART}")

# =========================
# 5. 最终数据产出 (CSV & JSON)
# =========================
if final_list:
    # 导出表格文件 (CSV) - 关键修复点
    print(f"📄 正在生成表格文件: {SAVE_CSV}...")
    with open(SAVE_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=final_list[0].keys())
        writer.writeheader()
        for row in final_list:
            row_copy = row.copy()
            row_copy["tags"] = " / ".join(row["tags"]) # 将列表转为字符串方便查看
            writer.writerow(row_copy)
    
    # 执行绘图
    generate_visualizations(final_list)

    # 导出 JSON
    with open(SAVE_JSON, "w", encoding="utf-8") as f:
        json.dump(final_list, f, ensure_ascii=False, indent=2)

print(f"\n🎉 任务完成！")
print(f"📁 已生成：{SAVE_CSV} (表格) 和 {SAVE_JSON} (数据)")
print(f"🖼️ 已生成：{SAVE_CHART} (统计图)")
