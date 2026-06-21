import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from hubspot_client import get_all_forms, get_form_submissions, CHANNEL_COLORS, CHANNEL_LABELS, BRAND

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

    with st.spinner("Loading forms..."):
        forms = get_all_forms()

    if not forms:
        st.error("No forms found.")
        return

    period = st.radio("Period", ["Today", "This week", "This month", "This quarter", "This year"], horizontal=True)
    now_tz = pd.Timestamp.now(tz="UTC")

    form_stats = []
    prog = st.progress(0, text="Loading submissions...")

    for i, form in enumerate(forms):
        fid   = form.get("id")
        fname = form.get("name", "Unknown")
        subs  = get_form_submissions(fid)

        sub_df = pd.DataFrame(subs)
        if sub_df.empty or "submittedAt" not in sub_df.columns:
            form_stats.append({"id": fid, "name": fname, "count": 0, "all_subs": None})
        else:
            sub_df["submitted_at"] = pd.to_datetime(sub_df["submittedAt"], unit="ms", utc=True)
            filtered = filter_by_period(sub_df, period, now_tz)
            form_stats.append({"id": fid, "name": fname, "count": len(filtered), "all_subs": sub_df})

        prog.progress((i + 1) / len(forms), text=f"Loading {i+1}/{len(forms)} forms...")

    prog.empty()

    # ── Top 10 ───────────────────────────────────────────────
    st.subheader("Top 10 Forms")
    stats_df = pd.DataFrame([{"name": s["name"], "count": s["count"]} for s in form_stats])
    top10    = stats_df.nlargest(10, "count").reset_index(drop=True)
    top10.index += 1

    if top10["count"].max() == 0:
        st.info("No submissions found for this period.")
    else:
        st.dataframe(
            top10.rename(columns={"name": "Form Name", "count": "Submissions"}),
            use_container_width=True, height=370
        )
        fig_top = px.bar(
            top10.reset_index(), x="count", y="name", orientation="h",
            labels={"count": "Submissions", "name": ""},
            color_discrete_sequence=[BRAND["primary"]],
        )
        fig_top.update_layout(
            yaxis=dict(autorange="reversed"),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
        )
        st.plotly_chart(fig_top, use_container_width=True)

    st.markdown("---")

    # ── Form detail ──────────────────────────────────────────
    st.subheader("Form Detail")

    form_names = [s["name"] for s in form_stats if s.get("all_subs") is not None]
    if not form_names:
        st.info("No form submission data available.")
        return

    selected_name = st.selectbox("Select a form", form_names)
    selected      = next((s for s in form_stats if s["name"] == selected_name), None)
    if not selected or selected.get("all_subs") is None:
        st.info("No submissions for this form.")
        return

    sub_df   = selected["all_subs"]
    total_all = len(sub_df)

    this_month   = len(filter_by_period(sub_df, "This month",   now_tz))
    this_quarter = len(filter_by_period(sub_df, "This quarter", now_tz))

    prev_start = (now_tz.replace(day=1) - timedelta(days=1)).replace(day=1)
    prev_end   = now_tz.replace(day=1)
    prev_count = len(sub_df[(sub_df["submitted_at"] >= prev_start) & (sub_df["submitted_at"] < prev_end)])
    delta_str  = f"+{((this_month-prev_count)/max(prev_count,1)*100):.0f}% vs last month" if prev_count else ""

    day_counts   = sub_df.groupby(sub_df["submitted_at"].dt.date).size()
    busiest_day  = day_counts.idxmax() if total_all else "-"
    busiest_cnt  = day_counts.max()    if total_all else 0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("All time",     f"{total_all:,}")
    m2.metric("This month",   f"{this_month:,}", delta_str)
    m3.metric("This quarter", f"{this_quarter:,}")
    m4.metric("Busiest day",  str(busiest_day), f"{busiest_cnt} submissions")

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Channel Distribution**")
        if "hs_analytics_source" in sub_df.columns:
            ch = sub_df["hs_analytics_source"].value_counts().reset_index()
            ch.columns = ["channel", "count"]
            ch["label"] = ch["channel"].map(CHANNEL_LABELS).fillna(ch["channel"])
            ch["pct"]   = (ch["count"] / ch["count"].sum() * 100).round(1)
            fig_ch = px.bar(
                ch, x="count", y="label", orientation="h",
                color="channel", color_discrete_map=CHANNEL_COLORS,
                text=ch["pct"].astype(str) + "%",
                labels={"count": "", "label": ""},
            )
            fig_ch.update_layout(showlegend=False, yaxis=dict(autorange="reversed"),
                                 plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", height=300)
            st.plotly_chart(fig_ch, use_container_width=True)
        else:
            st.info("Channel data not available.")

    with col2:
        st.markdown("**Historical Submissions — monthly by channel**")
        sub_df = sub_df.copy()
        sub_df["month"] = sub_df["submitted_at"].dt.to_period("M").apply(lambda r: r.start_time.strftime("%b %Y"))

        if "hs_analytics_source" in sub_df.columns:
            hist = sub_df.groupby(["month", "hs_analytics_source"]).size().reset_index(name="count")
            fig_h = px.bar(hist, x="month", y="count", color="hs_analytics_source",
                           color_discrete_map=CHANNEL_COLORS, barmode="stack",
                           labels={"month": "", "count": "Submissions", "hs_analytics_source": ""})
        else:
            hist = sub_df.groupby("month").size().reset_index(name="count")
            fig_h = px.bar(hist, x="month", y="count",
                           labels={"month": "", "count": "Submissions"},
                           color_discrete_sequence=[BRAND["primary"]])

        fig_h.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                            height=300, legend=dict(font=dict(size=10)))
        st.plotly_chart(fig_h, use_container_width=True)

    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()
