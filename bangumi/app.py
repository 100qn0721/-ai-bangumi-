import streamlit as st
import pandas as pd
import json
import os
import plotly.express as px

# =========================
# 1. 页面基础配置
# =========================
st.set_page_config(
    page_title="Bangumi 追番审计系统",
    page_icon="🎬",
    layout="wide"
)

# 自定义 CSS 增加蓝色框的美观度
st.markdown("""
    <style>
    .comment-box {
        background-color: #e8f4f9;
        border-left: 5px solid #0077b6;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0px;
    }
    </style>
    """, unsafe_allow_stdio=True)

# =========================
# 2. 数据加载逻辑
# =========================
@st.cache_data
def load_data():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(current_dir, "bangumi_data.json")
    
    if not os.path.exists(data_path):
        return None, None
        
    with open(data_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)
        
    if isinstance(raw_data, list):
        return "", pd.DataFrame(raw_data)
    
    user_bio = raw_data.get("user_info", {}).get("bio", "暂无简介")
    df = pd.DataFrame(raw_data.get("collections", []))
    return user_bio, df

bio, df = load_data()

# =========================
# 3. 侧边栏：个人名片
# =========================
st.sidebar.title("👤 个人主页")
if bio:
    st.sidebar.markdown("### 个人简介")
    st.sidebar.info(bio)

st.sidebar.divider()
st.sidebar.caption("数据同步自 Bangumi API v0")

# =========================
# 4. 主界面
# =========================
st.title("🎬 我的番剧审美审计看板")

if df is None or df.empty:
    st.error("❌ 未找到 bangumi_data.json 文件！")
else:
    # --- 数据概览 ---
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("总收藏数", len(df))
    with col2: st.metric("已看完", len(df[df['status'] == 2]))
    with col3: st.metric("平均评分", f"{df[df['my_rate'] > 0]['my_rate'].mean():.2f}")
    with col4: st.metric("最近活跃年份", df[df['year'] != "未知"]['year'].max())

    st.divider()

    # --- 筛选器 ---
    st.subheader("🔍 搜索与筛选")
    search_col, status_col, year_col = st.columns([2, 1, 1])
    with search_col:
        keyword = st.text_input("输入番剧名称关键词", "")
    with status_col:
        status_map = {1: "想看", 2: "看过", 3: "在看", 4: "搁置", 5: "抛弃"}
        selected_status = st.selectbox("观看状态", ["全部"] + list(status_map.values()))
    with year_col:
        all_years = sorted(df['year'].unique(), reverse=True)
        selected_year = st.selectbox("年份", ["全部项目"] + all_years)

    # 过滤数据
    f_df = df.copy()
    if keyword: f_df = f_df[f_df['name_cn'].str.contains(keyword, case=False, na=False)]
    if selected_status != "全部":
        rev_map = {v: k for k, v in status_map.items()}
        f_df = f_df[f_df['status'] == rev_map[selected_status]]
    if selected_year != "全部项目":
        f_df = f_df[f_df['year'] == selected_year]

    # --- 核心分析与展示 ---
    tab1, tab2 = st.tabs(["📊 审美分析图表", "✨ 追番动态与评价"])

    with tab1:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### 个人评分分布")
            r_df = f_df[f_df['my_rate'] > 0]
            if not r_df.empty:
                fig = px.histogram(r_df, x="my_rate", nbins=10, color_discrete_sequence=['#ff9999'])
                st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.markdown("#### 个人与站内评分对比")
            comp_df = f_df[(f_df['my_rate'] > 0) & (f_df['global_score'] > 0)]
            if not comp_df.empty:
                fig2 = px.scatter(comp_df, x="global_score", y="my_rate", hover_name="name_cn", color="my_rate")
                fig2.add_shape(type="line", x0=0, y0=0, x1=10, y1=10, line=dict(color="Red", dash="dash"))
                st.plotly_chart(fig2, use_container_width=True)

    with tab2:
        st.markdown(f"##### 共筛选出 {len(f_df)} 部作品")
        # 按照我的评分从高到低排序，如果有评价的排在前面
        f_df = f_df.sort_values(by=["my_rate", "global_score"], ascending=False)
        
        for _, row in f_df.iterrows():
            # 为每一部番剧创建一个可折叠的展示块
            score_text = f"⭐ {row['my_rate']}" if row['my_rate'] > 0 else "未评分"
            with st.expander(f"{row['name_cn']} ({row['year']}) —— {score_text}"):
                col_left, col_right = st.columns([1, 3])
                
                with col_left:
                    st.write(f"**站内平均分:** `{row['global_score']}`")
                    st.write(f"**观看状态:** {status_map.get(row['status'], '未知')}")
                    st.write(f"**标签:** {', '.join(row['tags'])}")
                
                with col_right:
                    if row['my_comment']:
                        st.markdown("**我的评价：**")
                        # 重点：这里就是你要的蓝色评价框
                        st.info(row['my_comment'])
                    else:
                        st.write("*暂无短评*")

# =========================
# 5. 底部
# =========================
st.divider()
st.caption("Powered by Zhang Jiechen | Bangumi 审计系统 V6.7")
