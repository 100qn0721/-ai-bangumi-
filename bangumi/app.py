import streamlit as st
import pandas as pd
import json
import os
import plotly.express as px

st.set_page_config(page_title="番剧分析 + 推荐", page_icon="🎬", layout="wide")

@st.cache_data
def load_data():
    path = os.path.join(os.path.dirname(__file__), "bangumi_data.json")
    if not os.path.exists(path):
        return None, None, None

    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    df = pd.DataFrame(raw.get("collections", []))
    ai = raw.get("ai_profile", {})
    rec = raw.get("recommendations", [])

    return df, ai, rec

df, ai_profile, recs = load_data()

st.title("🎬 番剧分析 + 推荐系统")

if df is None or df.empty:
    st.error("请先运行 bangumi.py")
    st.stop()

# =========================
# Tabs
# =========================
t1, t2, t3 = st.tabs(["📊 数据分析", "🧠 AI画像", "🔥 推荐"])

# =========================
# 数据分析
# =========================
with t1:
    st.metric("总数", len(df))
    st.metric("平均评分", f"{df[df['my_rate']>0]['my_rate'].mean():.2f}")

    fig = px.scatter(
        df[df['my_rate']>0],
        x="global_score",
        y="my_rate",
        hover_name="name_cn"
    )
    st.plotly_chart(fig)

# =========================
# AI画像
# =========================
with t2:
    st.json(ai_profile)

# =========================
# 推荐
# =========================
with t3:
    st.subheader("🔥 推荐番剧")

    if not recs:
        st.warning("暂无推荐")
    else:
        for r in recs:
            with st.expander(f"{r['name']} ⭐{r['score']}"):
                st.write(f"推荐标签：{r['tag']}")
