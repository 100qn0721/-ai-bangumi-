import streamlit as st
import pandas as pd
import json
import os
import plotly.express as px

st.set_page_config(page_title="Bangumi 追番审计", page_icon="🎬", layout="wide")

@st.cache_data
def load_data():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(current_dir, "bangumi_data.json")
    
    if not os.path.exists(data_path):
        return None, None
        
    try:
        with open(data_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
            
        if isinstance(raw_data, list):
            return "⚠️ 请运行最新版 bangumi.py 更新数据以显示简介", pd.DataFrame(raw_data)
        
        user_bio = raw_data.get("user_info", {}).get("bio", "暂无简介")
        df = pd.DataFrame(raw_data.get("collections", []))
        return user_bio, df
    except Exception as e:
        st.error(f"数据解析失败: {e}")
        return None, None

bio, df = load_data()

# =========================
# 侧边栏：个人名片
# =========================
st.sidebar.title("👤 个人主页")
if bio:
    st.sidebar.markdown("### 看番哲学")
    # 使用 code 块能完美保留你写的换行和颜文字
    st.sidebar.code(bio, language="text") 

st.sidebar.divider()
st.sidebar.caption("数据同步自 Bangumi API v0")

# =========================
# 主界面
# =========================
st.title("🎬 我的番剧审美审计看板")

if df is None or df.empty:
    st.warning("📡 正在等待数据上传或文件不存在...")
else:
    # --- 1. 指标卡片 ---
    c1, c2, c3 = st.columns(3)
    c1.metric("总收藏", len(df))
    c2.metric("已看完", len(df[df['status'] == 2]))
    c3.metric("平均评分", f"{df[df['my_rate'] > 0]['my_rate'].mean():.2f}")
    
    st.divider()

    # --- 2. 强大的高级筛选器 ---
    st.subheader("🔍 高级多维筛选")
    
    # 提取所有存在的年份和标签
    all_years = sorted([y for y in df['year'].unique() if y != "未知"], reverse=True)
    all_tags = set()
    for tags in df['tags'].dropna():
        if isinstance(tags, list):
            for t in tags: all_tags.add(t)
    all_tags = sorted(list(all_tags))

    # 第一排筛选：基础属性
    col_k, col_y, col_s, col_t = st.columns(4)
    with col_k:
        keyword = st.text_input("番剧名称 (可留空)", "")
    with col_y:
        sel_year = st.selectbox("首播年份", ["全部"] + all_years)
    with col_s:
        status_map = {"全部": -1, "想看": 1, "看过": 2, "在看": 3, "搁置": 4, "抛弃": 5}
        sel_status = st.selectbox("观看状态", list(status_map.keys()))
    with col_t:
        sel_tags = st.multiselect("类型标签 (可多选)", all_tags, placeholder="例如: 搞笑, 异世界")

    # 第二排筛选：评分区间滑动条
    col_rate1, col_rate2 = st.columns(2)
    with col_rate1:
        my_rate_range = st.slider("我的评分区间", 0, 10, (0, 10))
    with col_rate2:
        global_rate_range = st.slider("站内评分区间", 0.0, 10.0, (0.0, 10.0))

    # --- 执行过滤逻辑 ---
    f_df = df.copy()
    if keyword: f_df = f_df[f_df['name_cn'].str.contains(keyword, case=False, na=False)]
    if sel_year != "全部": f_df = f_df[f_df['year'] == sel_year]
    if sel_status != "全部": f_df = f_df[f_df['status'] == status_map[sel_status]]
    if sel_tags:
        # 只要包含所选标签中的任意一个即可
        f_df = f_df[f_df['tags'].apply(lambda tags: any(t in sel_tags for t in tags) if isinstance(tags, list) else False)]
    
    # 评分区间过滤
    f_df = f_df[(f_df['my_rate'] >= my_rate_range[0]) & (f_df['my_rate'] <= my_rate_range[1])]
    f_df = f_df[(f_df['global_score'] >= global_rate_range[0]) & (f_df['global_score'] <= global_rate_range[1])]

    st.markdown(f"**过滤结果：共匹配到 {len(f_df)} 部番剧**")

    # --- 3. 展示区 ---
    tab1, tab2 = st.tabs(["✨ 追番评价库", "📊 统计图表"])

    with tab1:
        rev_status_map = {v: k for k, v in status_map.items() if v != -1}
        # 默认按照我的评分排序，好番在前
        for _, row in f_df.sort_values("my_rate", ascending=False).iterrows():
            with st.expander(f"{row['name_cn']} —— ⭐{row['my_rate'] if row['my_rate']>0 else '未评'}"):
                st.write(f"**年份:** {row['year']} | **站内分:** {row['global_score']} | **状态:** {rev_status_map.get(row['status'], '未知')}")
                st.caption(f"标签: {', '.join(row['tags']) if isinstance(row['tags'], list) else '无'}")
                if row['my_comment']:
                    st.info(f"📝 {row['my_comment']}")
                else:
                    st.write("*暂无评价内容*")

    with tab2:
        if not f_df.empty:
            fig = px.histogram(f_df[f_df['my_rate']>0], x="my_rate", title="当前筛选条件下的评分分布", color_discrete_sequence=['#ff9999'])
            st.plotly_chart(fig, use_container_width=True)
