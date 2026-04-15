import streamlit as st
import pandas as pd
import json
import os
import plotly.express as px

st.set_page_config(page_title="张颉宸的番剧审计", page_icon="🎬", layout="wide")

# =========================
# 1. 加载包含 AI 画像的新数据
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
# 2. 侧边栏：个人名片与看番哲学
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

    # --- 新增：展示 AI 画像 ---
    if ai_profile:
        st.subheader("🧠 审美 AI 画像")
        with st.container(border=True):
            col_ai1, col_ai2, col_ai3, col_ai4 = st.columns(4)
            col_ai1.metric("打分风格", ai_profile.get('score_style', '未知'))
            # 将情绪比例转换成百分比
            col_ai2.metric("感性评价占比", f"{ai_profile.get('emotion_ratio', 0) * 100:.1f}%")
            
            # 评分偏差：如果你打分普遍比大众高，显示正号
            bias = ai_profile.get('avg_bias', 0)
            bias_str = f"+{bias}" if bias > 0 else f"{bias}"
            col_ai3.metric("全站评分偏差", bias_str)
            
            col_ai4.metric("平均给分", f"{ai_profile.get('avg_score', 0):.2f}")
            
            st.markdown(f"**🌟 核心偏好标签:** `{'` | `'.join(ai_profile.get('favorite_tags', []))}`")

    st.divider()

    # --- 高级分类筛选 ---
    with st.expander("🔍 开启多维看番记录筛选", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            keyword = st.text_input("搜索作品名称")
        with c2:
            years = sorted([y for y in df['year'].unique() if y != "未知"], reverse=True)
            sel_year = st.multiselect("出品年份", years)
        with c3:
            all_tags = sorted(list(set([t for tags in df['tags'] for t in tags])))
            sel_tags = st.multiselect("包含元素", all_tags)
        with c4:
            status_map = {1:"想看", 2:"看过", 3:"在看", 4:"搁置", 5:"抛弃"}
            sel_status = st.multiselect("观看状态", list(status_map.values()))

        r1, r2 = st.columns(2)
        with r1:
            my_range = st.slider("我的评分区间", 0, 10, (0, 10))
        with r2:
            gb_range = st.slider("站内评分区间", 0.0, 10.0, (0.0, 10.0))

    # --- 过滤数据 ---
    f_df = df.copy()
    if keyword: f_df = f_df[f_df['name_cn'].str.contains(keyword, case=False, na=False)]
    if sel_year: f_df = f_df[f_df['year'].isin(sel_year)]
    if sel_status: 
        inv_status = {v: k for k, v in status_map.items()}
        f_df = f_df[f_df['status'].isin([inv_status[s] for s in sel_status])]
    if sel_tags:
        f_df = f_df[f_df['tags'].apply(lambda x: any(t in sel_tags for t in x))]
    f_df = f_df[(f_df['my_rate'] >= my_range[0]) & (f_df['my_rate'] <= my_range[1])]
    f_df = f_df[(f_df['global_score'] >= gb_range[0]) & (f_df['global_score'] <= gb_range[1])]

    # --- 展示区 ---
    t1, t2 = st.tabs(["✨ 评价时光机 (按时间倒序)", "📊 审美分布分析"])

    with t1:
        st.write(f"当前条件检索到 {len(f_df)} 部作品")
        display_df = f_df.sort_values("updated_at", ascending=False) if 'updated_at' in f_df.columns else f_df
        
        for _, row in display_df.iterrows():
            with st.expander(f"{row['name_cn']} —— ⭐{row['my_rate'] if row['my_rate']>0 else '未评'}"):
                st.write(f"**最后更新:** {row.get('updated_at', '未知')} | **站内分:** {row['global_score']} | **年份:** {row['year']}")
                if row['my_comment']:
                    st.info(f"我的短评：{row['my_comment']}")
                st.caption(f"标签: {' / '.join(row['tags'])}")

    with t2:
        if not f_df.empty:
            fig = px.scatter(f_df[f_df['my_rate']>0], x="global_score", y="my_rate", 
                           hover_name="name_cn", size_max=15, 
                           labels={"global_score":"全站均分", "my_rate":"我的评分"})
            st.plotly_chart(fig, use_container_width=True)
