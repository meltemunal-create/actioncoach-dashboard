import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
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

def get_submission_count(form, period, now_tz):
    try:
        subs = get_form_submissions(form["id"])
        if not subs:
            return form["name"], 0
        sub_df = pd.DataFrame(subs)
        if "submittedAt" not in sub_df.columns:
            return form["name"], 0
        sub_df["submitted_at"] = pd.to_datetime(sub_df["submittedAt"], unit="ms", utc=True)
        count = len(filter_by_period(sub_df, period, now_tz))
        return form["name"], count
    except Exception:
        return form["name"], 0

def show():
    st.title("Form Performance")
    st.caption(f"Last updated: {datetime.now().strftime('%d %b %Y, %H:%M')}")

    with st.spinner("Loading forms..."):
        forms = get_all_forms()

    if not forms:
        st.error("No forms found.")
        return

    all_forms = forms
    ebook_forms = [f for f in forms if "lead magnet" in f.get("name", "").lower()]
    regular_forms = [f for f in forms if "lead magnet" not in f.get("name", "").lower()]

    st.caption(f"{len(forms)} forms found — {len(ebook_forms)} e-book (Lead Magnet), {len(regular_forms)} other")

    period = st.radio("Period", ["Today", "This week", "This month", "This quarter", "This year"], horizontal=True)
    now_tz = pd.Timestamp.now(tz="UTC")

    # ── TOP 10 GENEL ─────────────────────────────────────────
    st.subheader("Top 10 Forms")
    if st.button("🔍 Load Top 10"):
        progress = st.progress(0, text="Loading submissions...")
        results = []
        done = 0
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(get_submission_count, f, period, now_tz): f for f in all_forms}
            for future in as_completed(futures):
                name, count = future.result()
                results.append({"Form Name": name, "Submissions": count})
                done += 1
                progress.progress(done / len(all_forms), text=f"Loading {done}/{len(all_forms)}...")
        progress.empty()
        top10 = pd.DataFrame(results).nlargest(10, "Submissions").reset_index(drop=True)
        top10.index += 1
        st.dataframe(top10, use_container_width=True)
        fig = px.bar(top10.reset_index(), x="Submissions", y="Form Name", orientation="h",
                     color_discrete_sequence=[BRAND["primary"]])
        fig.update_layout(yaxis=dict(autorange="reversed"), plot_bgcolor="rgba(0,0,0,0)",
                          paper_bgcolor="rgba(0,0,0,0)", showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Click 'Load Top 10' to see the most submitted forms for the selected period.")

    st.markdown("---")

    # ── TOP 10 E-BOOK ─────────────────────────────────────────
    st.subheader("Top 10 E-Books (Lead Magnet)")
    if st.button("🔍 Load Top 10 E-Books"):
        progress2 = st.progress(0, text="Loading e-book submissions...")
        results2 = []
        done2 = 0
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures2 = {executor.submit(get_submission_count, f, period, now_tz): f for f in ebook_forms}
            for future in as_completed(futures2):
                name, count = future.result()
                results2.append({"Form Name": name, "Submissions": count})
                done2 += 1
                progress2.progress(done2 / len(ebook_forms), text=f"Loading {done2}/{len(ebook_forms)}...")
        progress2.empty()
        top10_ebook = pd.DataFrame(results2).nlargest(10, "Submissions").reset_index(drop=True)
        top10_ebook.index += 1
        # Form adından "Lead Magnet - " kısmını temizle
        top10_ebook["Form Name"] = top10_ebook["Form Name"].str.replace("Lead Magnet - ", "", regex=False)
        st.dataframe(top10_ebook, use_container_width=True)
        fig2 = px.bar(top10_ebook.reset_index(), x="Submissions", y="Form Name", orientation="h",
                      color_discrete_sequence=[BRAND["blue"]])
        fig2.update_layout(yaxis=dict(autorange="reversed"), plot_bgcolor="rgba(0,0,0,0)",
                           paper_bgcolor="rgba(0,0,0,0)", showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Click 'Load Top 10 E-Books' to see the most downloaded e-books.")

    st.markdown("---")

    # ── FORM DETAY ───────────────────────────────────────────
    st.subheader("Form Detail")
    form_names = [f.get("name", "Unknown") for f in all_forms]
    form_map = {f.get("name", "Unknown"): f.get("id") for f in all_forms}
    selected_name = st.selectbox("Select a form", ["— select —"] + form_names)

    if selected_name == "— select —":
        st.info("Select a form above to load its submissions.")
        return

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
    total_all    = len(sub_df)
    filtered     = len(filter_by_period(sub_df, period, now_tz))
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
    sub_df2["month_sort"] = sub_df2["submitted_at"].dt.to_period("M").apply(
        lambda r: r.start_time)
    hist = sub_df2.groupby(["month", "month_sort"]).size().reset_index(name="count")
    month_order = hist.sort_values("month_sort")["month"].tolist()
    fig_h = px.bar(hist, x="month", y="count",
                   category_orders={"month": month_order},
                   labels={"month": "", "count": "Submissions"},
                   color_discrete_sequence=[BRAND["primary"]])
    fig_h.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", height=300)
    st.plotly_chart(fig_h, use_container_width=True)

    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()
