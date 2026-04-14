import streamlit as st
import pandas as pd
import json
import os
import plotly.express as px

# =========================
# 1. 核心配置
# =========================
st.set_page_config(page_title="ZhangJiechen's Anime Hub", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .stExpander { border: 1px solid #f0f2f6; border-radius: 8px; margin-bottom: 5px; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data
def load_data():
    if not os.path.exists("bangumi_data.json"): return None
    with open("bangumi_data.json", "r", encoding="utf-8") as f:
        return json.load(f)

raw_data = load_data()
if not raw_data:
    st.error("❌ 数据文件不存在，请确保 bangumi_data.json 在同一目录下")
    st.stop()

df = pd.DataFrame(raw_data)

# 将年份转换为数字，方便过滤（处理非数字年份或'未知'的情况）
df['year_num'] = pd.to_numeric(df['year'], errors='coerce').fillna(0)

# 提取所有不重复的标签，用于“种类分类”
all_unique_tags = sorted(list(set(tag for tags in df['tags'] for tag in tags if tag)))

# =========================
# 2. 侧边栏：全能过滤器
# =========================
st.sidebar.title("🎬 审计过滤器")

# (1) 状态过滤
status_map = {1:"想看", 2:"看过", 3:"在看", 4:"搁置"}
selected_status = st.sidebar.multiselect("观看状态", options=[1,2,3,4], default=[2,3], format_func=lambda x: status_map[x])

# (2) 评分过滤
score_range = st.sidebar.slider("我的评分范围", min_value=0, max_value=10, value=(0, 10))

# (3) 年限过滤
min_y = int(df[df['year_num'] > 1900]['year_num'].min()) if not df[df['year_num'] > 1900].empty else 2000
max_y = int(df['year_num'].max()) if not df.empty else 2026
year_range = st.sidebar.slider("作品年限", min_y, max_y, (min_y, max_y))

# (4) 种类/标签过滤
selected_tags = st.sidebar.multiselect("番剧种类 (包含以下任意标签)", options=all_unique_tags)

# --- 应用所有过滤条件 ---
mask = df['status'].isin(selected_status)
mask &= (df['year_num'] >= year_range[0]) & (df['year_num'] <= year_range[1])
mask &= (df['my_rate'] >= score_range[0]) & (df['my_rate'] <= score_range[1])

if selected_tags:
    # 只要作品的标签中包含用户选择的任意一个标签，就保留
    mask &= df['tags'].apply(lambda x: any(tag in selected_tags for tag in x))

df_filtered = df[mask].copy()

# =========================
# 3. 主界面布局
# =========================
st.title("🎬 个人动画数据审计中心")

m1, m2, m3, m4 = st.columns(4)
m1.metric("入库总数", len(df))
m2.metric("当前筛选", len(df_filtered))
avg_val = df_filtered[df_filtered['my_rate']>0]['my_rate'].mean()
m3.metric("平均给分", f"{avg_val:.2f}" if not pd.isna(avg_val) else "N/A")
bias_val = (df_filtered['my_rate'] - df_filtered['global_score']).mean()
m4.metric("审美偏差", f"{bias_val:+.2f}")

st.divider()

# =========================
# 4. 交互式图表
# =========================
c1, c2 = st.columns([6, 4])

with c1:
    st.subheader("📊 评分分布 (悬停查看作品)")
    plot_df = df_filtered[df_filtered['my_rate'] > 0].copy()
    if not plot_df.empty:
        fig = px.histogram(
            plot_df, x="my_rate", nbins=10, color_discrete_sequence=['#FF4B4B'],
            labels={'my_rate': '我的评分', 'count': '作品数量'},
            hover_name="name_cn", hover_data={"my_rate": True, "global_score": True, "year": True}
        )
        fig.update_layout(bargap=0.1, margin=dict(l=10, r=10, t=10, b=10))
        fig.update_traces(hovertemplate="<b>%{hovertext}</b><br>我的评分: %{x}<br>全站评分: %{customdata[0]}<extra></extra>")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.write("当前筛选条件下无评分数据")

with c2:
    st.subheader("🏷️ 核心喜好标签")
    all_tags_filtered = []
    for t in df_filtered['tags']: all_tags_filtered.extend(t)
    tag_counts = pd.Series(all_tags_filtered).value_counts().head(12)
    if not tag_counts.empty:
        fig_tag = px.bar(tag_counts, x=tag_counts.values, y=tag_counts.index, 
                         orientation='h', color=tag_counts.values, color_continuous_scale='Reds',
                         labels={'x': '作品数', 'y': '标签'})
        fig_tag.update_layout(showlegend=False)
        st.plotly_chart(fig_tag, use_container_width=True)

# =========================
# 5. 全局评价审计墙
# =========================
st.divider()
st.subheader(f"🔍 全局评价审计墙 (共 {len(df_filtered)} 部)")
q = st.text_input("搜索番名、年份或评价：")

if q:
    search_df = df_filtered[df_filtered.apply(lambda row: q.lower() in str(row).lower(), axis=1)]
else:
    # 核心修改：移除 .head(30)，显示全局过滤后的数据
    search_df = df_filtered.sort_values(by="my_rate", ascending=False)

# 为了防止浏览器卡死，加上一个小提示
if len(search_df) > 500:
    st.caption("⚠️ 当前显示数量较多，向下滚动可能需要加载时间。")

for _, row in search_df.iterrows():
    rate_str = f"⭐ {row['my_rate']}" if row['my_rate'] > 0 else "无评分"
    with st.expander(f"{rate_str} | {row['name_cn']} ({row['year']})"):
        col_l, col_r = st.columns([1, 3])
        with col_l:
            st.write(f"**全站排名:** {row['global_rank']}")
            st.write(f"**全站评分:** {row['global_score']}")
            st.write(f"**标签:** {' / '.join(row['tags'])}")
        with col_r:
            comment_text = row.get('my_comment')
            if pd.isna(comment_text) or str(comment_text).strip() == "" or comment_text is None:
                box_type = st.warning 
                final_comment = "尚未评价"
            else:
                box_type = st.info 
                final_comment = comment_text
            box_type(f"**我的评价:** \n\n {final_comment}")