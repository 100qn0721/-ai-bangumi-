import streamlit as st
import pandas as pd
import json
import os
import plotly.express as px

# =========================
# 1. 页面配置
# =========================
st.set_page_config(page_title="Bangumi 追番审计", page_icon="🎬", layout="wide")

# =========================
# 2. 强力兼容的数据加载逻辑
# =========================
@st.cache_data
def load_data():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(current_dir, "bangumi_data.json")
    
    if not os.path.exists(data_path):
        return None, None
        
    try:
        with open(data_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
            
        # --- 核心：判断是旧版列表还是新版字典 ---
        if isinstance(raw_data, list):
            # 如果是旧版（纯列表），简介设为空，数据直接转 DataFrame
            return "（请更新数据以显示简介）", pd.DataFrame(raw_data)
        
        # 如果是新版字典结构
        user_bio = raw_data.get("user_info", {}).get("bio", "暂无简介")
        df = pd.DataFrame(raw_data.get("collections", []))
        return user_bio, df
    except Exception as e:
        st.error(f"数据解析失败: {e}")
        return None, None

bio, df = load_data()

# =========================
# 3. 侧边栏：个人名片
# =========================
st.sidebar.title("👤 个人主页")
if bio:
    st.sidebar.markdown("### 个人简介")
    st.sidebar.info(bio) # 这里就是你要的蓝色框

st.sidebar.divider()
st.sidebar.caption("数据同步自 Bangumi API v0")

# =========================
# 4. 主界面
# =========================
st.title("🎬 我的番剧审美审计看板")

if df is None or df.empty:
    st.warning("📡 正在等待数据上传或文件不存在...")
else:
    # 指标卡片
    c1, c2, c3 = st.columns(3)
    c1.metric("总收藏", len(df))
    c2.metric("已看完", len(df[df['status'] == 2]))
    c3.metric("平均评分", f"{df[df['my_rate'] > 0]['my_rate'].mean():.2f}")

    # 筛选器
    keyword = st.text_input("🔍 搜索番剧名称", "")
    
    # 过滤数据
    f_df = df.copy()
    if keyword:
        f_df = f_df[f_df['name_cn'].str.contains(keyword, case=False, na=False)]

    # 展示标签页
    tab1, tab2 = st.tabs(["📊 统计图表", "✨ 追番动态与评价"])

    with tab1:
        if not f_df.empty:
            fig = px.histogram(f_df[f_df['my_rate']>0], x="my_rate", title="评分分布", color_discrete_sequence=['#ff9999'])
            st.plotly_chart(fig, use_container_width=True)

    with tab2:
        # 这里是显示蓝色评价框的核心区域
        status_map = {1: "想看", 2: "看过", 3: "在看", 4: "搁置", 5: "抛弃"}
        for _, row in f_df.sort_values("my_rate", ascending=False).iterrows():
            with st.expander(f"{row['name_cn']} —— ⭐{row['my_rate'] if row['my_rate']>0 else '未评'}"):
                st.write(f"**年份:** {row['year']} | **站内分:** {row['global_score']}")
                if row['my_comment']:
                    # 这里是蓝色框评价
                    st.info(f"我的评价：\n\n {row['my_comment']}")
                else:
                    st.write("*暂无评价内容*")
