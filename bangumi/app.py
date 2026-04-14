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

# =========================
# 2. 数据加载逻辑 (适配 V6.7 嵌套结构)
# =========================
@st.cache_data
def load_data():
    # 获取 app.py 所在的绝对路径，确保在云端也能找到 json
    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(current_dir, "bangumi_data.json")
    
    if not os.path.exists(data_path):
        return None, None
        
    with open(data_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)
        
    # 处理 V6.7 之前的旧格式兼容性
    if isinstance(raw_data, list):
        return "", pd.DataFrame(raw_data)
    
    # 解析 V6.7 的新格式
    user_bio = raw_data.get("user_info", {}).get("bio", "暂无简介")
    df = pd.DataFrame(raw_data.get("collections", []))
    return user_bio, df

# 加载数据
bio, df = load_data()

# =========================
# 3. 侧边栏：个人名片
# =========================
st.sidebar.title("👤 个人主页")
if bio:
    st.sidebar.markdown("### 个人简介")
    # 使用 code 块或 info 框来展示你的看番哲学，保留换行和格式
    st.sidebar.info(bio)
else:
    st.sidebar.warning("未在 JSON 中找到个人简介，请检查脚本版本。")

st.sidebar.divider()
st.sidebar.caption("数据同步自 Bangumi API v0")

# =========================
# 4. 主界面：核心看板
# =========================
st.title("🎬 我的番剧审美审计看板")

if df is None or df.empty:
    st.error("❌ 未找到 bangumi_data.json 文件，请先运行同步脚本！")
else:
    # --- 数据概览卡片 ---
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("总收藏数", len(df))
    with col2:
        watched_count = len(df[df['status'] == 2])
        st.metric("已看完", watched_count)
    with col3:
        avg_score = df[df['my_rate'] > 0]['my_rate'].mean()
        st.metric("平均评分", f"{avg_score:.2f}")
    with col4:
        current_year = df[df['year'] != "未知"]['year'].max()
        st.metric("最近活跃年份", current_year)

    st.divider()

    # --- 筛选器 ---
    st.subheader("🔍 快速筛选与检索")
    search_col, status_col = st.columns([3, 1])
    with search_col:
        keyword = st.text_input("输入番剧名称关键词", "")
    with status_col:
        status_map = {1: "想看", 2: "看过", 3: "在看", 4: "搁置", 5: "抛弃"}
        selected_status_name = st.selectbox("观看状态", ["全部"] + list(status_map.values()))

    # 执行过滤
    filtered_df = df.copy()
    if keyword:
        filtered_df = filtered_df[filtered_df['name_cn'].str.contains(keyword, case=False, na=False)]
    if selected_status_name != "全部":
        rev_status_map = {v: k for k, v in status_map.items()}
        filtered_df = filtered_df[filtered_df['status'] == rev_status_map[selected_status_name]]

    # --- 核心图表区 ---
    tab1, tab2 = st.tabs(["📊 审美分析", "📋 数据详表"])

    with tab1:
        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
            st.markdown("#### 个人评分分布")
            # 过滤掉 0 分（未评分）的数据
            rated_df = filtered_df[filtered_df['my_rate'] > 0]
            if not rated_df.empty:
                fig_hist = px.histogram(rated_df, x="my_rate", nbins=10, 
                                      labels={'my_rate':'分值'}, 
                                      color_discrete_sequence=['#ff9999'])
                st.plotly_chart(fig_hist, use_container_width=True)
            else:
                st.write("暂无评分数据")

        with chart_col2:
            st.markdown("#### 个人评分 vs 站内平均分")
            # 过滤掉 0 分数据进行对比
            compare_df = filtered_df[(filtered_df['my_rate'] > 0) & (filtered_df['global_score'] > 0)]
            if not compare_df.empty:
                fig_scatter = px.scatter(compare_df, x="global_score", y="my_rate", 
                                       hover_name="name_cn",
                                       labels={'global_score':'全站平均分', 'my_rate':'我的评分'},
                                       color="my_rate", color_continuous_scale="Viridis")
                # 添加 1:1 参照线
                fig_scatter.add_shape(type="line", x0=0, y0=0, x1=10, y1=10, 
                                    line=dict(color="Red", dash="dash"))
                st.plotly_chart(fig_scatter, use_container_width=True)
            else:
                st.write("数据不足，无法生成对比图")

    with tab2:
        # --- 数据表格展示 ---
        st.markdown(f"找到 {len(filtered_df)} 条记录")
        
        # 整理表格列名，让它更好看
        display_df = filtered_df.copy()
        display_df['status'] = display_df['status'].map(status_map)
        display_df['tags'] = display_df['tags'].apply(lambda x: " | ".join(x) if isinstance(x, list) else x)
        
        # 重新排序并重命名
        display_df = display_df[['name_cn', 'year', 'my_rate', 'global_score', 'status', 'my_comment', 'tags']]
        display_df.columns = ['番剧名称', '年份', '我的评分', '站内评分', '状态', '我的短评', '标签']

        st.dataframe(display_df, use_container_width=True, height=600)

# =========================
# 5. 版权底部
# =========================
st.divider()
st.caption("Developed by Zhang Jiechen | 基于 Streamlit & Bangumi API")
