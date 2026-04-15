import streamlit as st
import pandas as pd
import json
import os
import plotly.express as px

st.set_page_config(page_title="张颉宸的番剧审计", page_icon="🎬", layout="wide")

# =========================
# 1. 加载数据
# =========================
@st.cache_data
def load_data():
    data_path = os.path.join(os.path.dirname(__file__), "bangumi_data.json")
    if not os.path.exists(data_path): return None, None, None
    with open(data_path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    
    if isinstance(raw, list): 
        return "请更新数据", pd.DataFrame(raw), None
    
    bio = raw.get("user_info", {}).get("bio", "")
    df = pd.DataFrame(raw.get("collections", []))
    ai_profile = raw.get("ai_profile", None)
    return bio, df, ai_profile

bio, df, ai_profile = load_data()

# =========================
# 2. 侧边栏
# =========================
st.sidebar.title("👤 个人主页")
if bio:
    st.sidebar.markdown("### 看番哲学")
    st.sidebar.info(bio)

st.sidebar.divider()
st.sidebar.caption("Powered by Bangumi API & AI Engine")

# =========================
# 3. 主界面
# =========================
if df is None or df.empty:
    st.error("未找到数据，请运行脚本并上传 JSON！")
else:
    st.title("🎬 番剧审美审计与 AI 洞察")
    
    # 顶部基础指标
    m1, m2, m3 = st.columns(3)
    m1.metric("总收藏数", len(df))
    m2.metric("已看完", len(df[df['status'] == 2]))
    m3.metric("近期活跃", df['updated_at'].max()[:10] if 'updated_at' in df.columns else "未知")

    # --- AI 画像区 ---
    if ai_profile:
        with st.expander("🧠 查看我的 AI 审美画像", expanded=False):
            col_ai1, col_ai2, col_ai3, col_ai4 = st.columns(4)
            col_ai1.metric("打分风格", ai_profile.get('score_style', '未知'))
            col_ai2.metric("感性评价占比", f"{ai_profile.get('emotion_ratio', 0) * 100:.1f}%")
            bias = ai_profile.get('avg_bias', 0)
            col_ai3.metric("全站评分偏差", f"+{bias}" if bias > 0 else f"{bias}")
            col_ai4.metric("平均给分", f"{ai_profile.get('avg_score', 0):.2f}")
            st.markdown(f"**🌟 核心偏好标签:** `{'` | `'.join(ai_profile.get('favorite_tags', []))}`")

    st.divider()

    # --- 搜索与筛选区 ---
    with st.container():
        c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
        with c1:
            keyword = st.text_input("🔍 搜索作品名称", placeholder="输入番名关键词...")
        with c2:
            years = sorted([y for y in df['year'].unique() if y != "未知"], reverse=True)
            sel_year = st.multiselect("📅 年份", years)
        with c3:
            all_tags = sorted(list(set([t for tags in df['tags'] for t in tags])))
            sel_tags = st.multiselect("🏷️ 标签", all_tags)
        with c4:
            status_map = {1:"想看", 2:"看过", 3:"在看", 4:"搁置", 5:"抛弃"}
            sel_status = st.multiselect("📺 状态", list(status_map.values()))

    # --- 排序控制区（这是你要的新功能） ---
    st.write("---")
    sort_col1, sort_col2 = st.columns([1, 2])
    with sort_col1:
        sort_method = st.selectbox(
            "🔃 排序方式",
            ["最新动态", "我的评分 (高→低)", "我的评分 (低→高)", "全站评分", "放送年份 (新→旧)", "放送年份 (旧→新)"]
        )

    # --- 数据过滤逻辑 ---
    f_df = df.copy()
    if keyword: f_df = f_df[f_df['name_cn'].str.contains(keyword, case=False, na=False)]
    if sel_year: f_df = f_df[f_df['year'].isin(sel_year)]
    if sel_status: 
        inv_status = {v: k for k, v in status_map.items()}
        f_df = f_df[f_df['status'].isin([inv_status[s] for s in sel_status])]
    if sel_tags:
        f_df = f_df[f_df['tags'].apply(lambda x: any(t in sel_tags for t in x))]

    # --- 数据排序逻辑 ---
    sort_map = {
        "最新动态": ("updated_at", False),
        "我的评分 (高→低)": ("my_rate", False),
        "我的评分 (低→高)": ("my_rate", True),
        "全站评分": ("global_score", False),
        "放送年份 (新→旧)": ("year", False),
        "放送年份 (旧→新)": ("year", True)
    }
    sort_key, is_asc = sort_map[sort_method]
    
    # 针对年份“未知”的处理：排到最后
    if "year" in sort_key:
        f_df['temp_year'] = f_df['year'].replace("未知", "0000")
        f_df = f_df.sort_values('temp_year', ascending=is_asc).drop(columns=['temp_year'])
    else:
        f_df = f_df.sort_values(sort_key, ascending=is_asc)

    # --- 展示展示 ---
    tab_list, tab_stats = st.tabs(["✨ 番剧列表", "📊 数据分布"])

    with tab_list:
        st.write(f"共找到 {len(f_df)} 部作品")
        for _, row in f_df.iterrows():
            with st.expander(f"{row['name_cn']} {'⭐'*int(row['my_rate']//2) if row['my_rate']>0 else '（未评分）'}"):
                col_info, col_comment = st.columns([1, 2])
                with col_info:
                    st.write(f"**我的评分:** {row['my_rate'] if row['my_rate']>0 else 'N/A'}")
                    st.write(f"**全站评分:** {row['global_score']}")
                    st.write(f"**放送年份:** {row['year']}")
                    st.write(f"**最后动态:** {row.get('updated_at', '未知')[:16]}")
                with col_comment:
                    if row['my_comment']:
                        st.info(f"**评价:** {row['my_comment']}")
                    else:
                        st.caption("暂无评价内容")
                    st.caption(f"标签: {' / '.join(row['tags'])}")

    with tab_stats:
        if not f_df.empty:
            st.subheader("我的审美 vs 大众审美")
            fig = px.scatter(f_df[f_df['my_rate']>0], x="global_score", y="my_rate", 
                           hover_name="name_cn", size_max=15, 
                           labels={"global_score":"全站均分", "my_rate":"我的评分"},
                           color="my_rate", color_continuous_scale="Viridis")
            st.plotly_chart(fig, use_container_width=True)
