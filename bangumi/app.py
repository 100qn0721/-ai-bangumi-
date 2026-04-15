import streamlit as st
import pandas as pd
import json
import os
import plotly.express as px

st.set_page_config(page_title="ZhangJiechen 的番剧审计", page_icon="🎬", layout="wide")

# 加载数据
@st.cache_data
def load_data():
    data_path = os.path.join(os.path.dirname(__file__), "bangumi_data.json")
    if not os.path.exists(data_path): return None, None
    with open(data_path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    if isinstance(raw, list): return "请更新数据", pd.DataFrame(raw)
    return raw.get("user_info", {}).get("bio", ""), pd.DataFrame(raw.get("collections", []))

bio, df = load_data()

# --- 侧边栏：个人介绍 ---
st.sidebar.title("👤 个人介绍")
if bio:
    # 蓝色背景框展示你的看番宣言
    st.sidebar.info(bio)

st.sidebar.divider()
st.sidebar.caption("数据来源：Bangumi API v0")

# --- 主界面 ---
if df is None or df.empty:
    st.error("未找到数据，请运行脚本并上传 JSON！")
else:
    st.title("🎬 番剧审美审计看板")
    
    # 顶部指标
    m1, m2, m3 = st.columns(3)
    m1.metric("总收藏", len(df))
    m2.metric("平均给分", f"{df[df['my_rate']>0]['my_rate'].mean():.2f}")
    m3.metric("最近更新", df['updated_at'].max()[:10] if 'updated_at' in df.columns else "未知")

    # --- 高级分类筛选 ---
    with st.expander("🔍 开启高级筛选（年代/类型/评分）", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            years = sorted([y for y in df['year'].unique() if y != "未知"], reverse=True)
            sel_year = st.multiselect("出品年份", years)
        with c2:
            # 提取所有标签
            all_tags = sorted(list(set([t for tags in df['tags'] for t in tags])))
            sel_tags = st.multiselect("番剧类型", all_tags)
        with c3:
            status_map = {1:"想看", 2:"看过", 3:"在看", 4:"搁置", 5:"抛弃"}
            sel_status = st.multiselect("观看状态", list(status_map.values()))

        r1, r2 = st.columns(2)
        with r1:
            my_range = st.slider("我的评分区间", 0, 10, (0, 10))
        with r2:
            gb_range = st.slider("站内评分区间", 0.0, 10.0, (0.0, 10.0))

    # --- 过滤逻辑 ---
    f_df = df.copy()
    if sel_year: f_df = f_df[f_df['year'].isin(sel_year)]
    if sel_status: 
        inv_status = {v: k for k, v in status_map.items()}
        f_df = f_df[f_df['status'].isin([inv_status[s] for s in sel_status])]
    if sel_tags:
        f_df = f_df[f_df['tags'].apply(lambda x: any(t in sel_tags for t in x))]
    f_df = f_df[(f_df['my_rate'] >= my_range[0]) & (f_df['my_rate'] <= my_range[1])]
    f_df = f_df[(f_df['global_score'] >= gb_range[0]) & (f_df['global_score'] <= gb_range[1])]

    # --- 展示标签页 ---
    t1, t2 = st.tabs(["✨ 评价时光机 (按时间排序)", "📊 审美分布图"])

    with t1:
        st.write(f"当前筛选下有 {len(f_df)} 部作品")
        # 按更新时间倒序排列，实现“时光机”效果
        display_df = f_df.sort_values("updated_at", ascending=False) if 'updated_at' in f_df.columns else f_df
        
        for _, row in display_df.iterrows():
            with st.expander(f"{row['name_cn']} —— ⭐{row['my_rate'] if row['my_rate']>0 else '未评'}"):
                st.write(f"**更新时间:** {row.get('updated_at', '未知')}")
                st.write(f"**站内评分:** {row['global_score']} | **年份:** {row['year']}")
                if row['my_comment']:
                    st.info(f"我的评价：{row['my_comment']}")
                st.caption(f"标签: {' / '.join(row['tags'])}")

    with t2:
        if not f_df.empty:
            fig = px.scatter(f_df[f_df['my_rate']>0], x="global_score", y="my_rate", 
                           hover_name="name_cn", size_max=15, 
                           labels={"global_score":"全站均分", "my_rate":"我的评分"})
            st.plotly_chart(fig, use_container_width=True)
