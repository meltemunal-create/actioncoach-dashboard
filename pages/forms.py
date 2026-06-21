import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from hubspot_client import get_all_forms, get_form_submissions, BRAND

def filter_by_period(df, period, now):
    if period == "Today":
        cutoff = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "This week":
        cutoff = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "This month":
        cutoff = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif period == "This quarter":
        q_month = ((now.month - 1) // 3) * 3 + 1
        cutoff = now.replace(month=q_month, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        cutoff = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    return df[df["submitted_at"] >= cutoff]

def show():
    st.title("Form Performance")
    st.caption(f"Last updated: {datetime.now().strftime('%d %b %Y, %H:%M')}")

    with st.spinner("Loading form list..."):
        forms = get_all_forms()

    if not forms:
        st.error("No forms found.")
        return

    st.caption(f"{len(forms)} forms found")

    period = st.radio("Period", ["Today", "This week", "This month", "This quarter", "This year"], horizontal=True)
    now_tz = pd.Timestamp.now(tz="UTC")

    form_names = [f.get("name", "Unknown") for f in forms]
    form_map = {f.get("name", "Unknown"): f.get("id") for f in forms}

    selected_name = st.selectbox("Select a form", ["— select —"] + form_names)

    if selected_name == "— select —":
        st.info("Select a form above to load its submissions.")
        return

    st.markdown("---")
    st.subheader(f"{selected_name}")
    form_id = form_map[selected_name]

    with st.spinner("Loading submissions..."):
        subs = get_form_submissions(form_id)

    if not subs:
        st.info("No submissions found for this form.")
        return

    sub_df = pd.DataFrame(subs)
    if "submittedAt" not in sub_df.columns:
        st.info("No submission data available.")
        return

    sub_df["submitted_at"] = pd.to_datetime(sub_df["submittedAt"], unit="ms", utc=True)
    total_all = len(sub_df)
    filtered  = len(filter_by_period(sub_df, period, now_tz))

    this_month   = len(filter_by_period(sub_df, "This month",   now_tz))
    this_quarter = len(filter_by_period(sub_df, "This quarter", now_tz))

    prev_start = (now_tz.replace(day=1) - timedelta(days=1)).replace(day=1)
    prev_end   = now_tz.replace(day=1)
    prev_count = len(sub_df[(sub_df["submitted_at"] >= prev_start) & (sub_df["submitted_at"] < prev_end)])
    delta_str  = f"+{((this_month-prev_count)/max(prev_count,1)*100):.0f}% vs last month" if prev_count else ""

    day_counts  = sub_df.groupby(sub_df["submitted_at"].dt.date).size()
    busiest_day = day_counts.idxmax() if total_all else "-"
    busiest_cnt = day_counts.max() if total_all else 0

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("All time",     f"{total_all:,}")
    m2.metric(period,         f"{filtered:,}")
    m3.metric("This month",   f"{this_month:,}", delta_str)
    m4.metric("This quarter", f"{this_quarter:,}")
    m5.metric("Busiest day",  str(busiest_day), f"{busiest_cnt} subs")

    st.markdown("---")

    st.markdown("**Historical Submissions — monthly**")
    sub_df2 = sub_df.copy()
    sub_df2["month"] = sub_df2["submitted_at"].dt.to_period("M").apply(
        lambda r: r.start_time.strftime("%b %Y"))
    hist = sub_df2.groupby("month").size().reset_index(name="count")
    fig_h = px.bar(hist, x="month", y="count",
                   labels={"month": "", "count": "Submissions"},
                   color_discrete_sequence=[BRAND["primary"]])
    fig_h.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", height=300)
    st.plotly_chart(fig_h, use_container_width=True)

    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()
