import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from hubspot_client import get_contact_counts, get_marketing_trend, BRAND

def show():
    st.title("General Data Overview")
    st.caption(f"Last updated: {datetime.now().strftime('%d %b %Y, %H:%M')}")

    with st.spinner("Loading contact summary..."):
        counts = get_contact_counts()

    total        = counts["total"]
    marketing    = counts["marketing"]
    unsubscribed = counts["unsubscribed"]
    bounced      = counts["bounced"]
    aktif        = marketing - unsubscribed - bounced
    non_mkt      = total - aktif

    st.subheader("Contact Summary")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Contacts",         f"{total:,}")
    c2.metric("Marketing Contacts",     f"{aktif:,}",   f"{aktif/max(total,1)*100:.1f}% of total")
    c3.metric("Non-Marketing Contacts", f"{non_mkt:,}", f"{non_mkt/max(total,1)*100:.1f}% of total")

    st.markdown("")
    d1, d2 = st.columns(2)
    d1.metric("Unsubscribed", f"{unsubscribed:,}", f"-{unsubscribed/max(marketing,1)*100:.1f}% of marketing")
    d2.metric("Bounced",      f"{bounced:,}",      f"-{bounced/max(marketing,1)*100:.1f}% of marketing")

    st.markdown("---")

    with st.spinner("Loading trend data..."):
        trend_dates = get_marketing_trend()

    if not trend_dates:
        st.info("No trend data available.")
        if st.button("🔄 Refresh"):
            st.cache_data.clear()
            st.rerun()
        return

    df = pd.DataFrame({"createdate": pd.to_datetime(trend_dates, errors="coerce", utc=True)})
    df = df.dropna()
    now = pd.Timestamp.now(tz="UTC")

    st.subheader("Marketing Contact Growth")
    def count_since(days):
        return df[df["createdate"] >= now - timedelta(days=days)].shape[0]

    g1, g2, g3, g4, g5 = st.columns(5)
    g1.metric("Daily",     f"+{count_since(1):,}")
    g2.metric("Weekly",    f"+{count_since(7):,}")
    g3.metric("Monthly",   f"+{count_since(30):,}")
    g4.metric("Quarterly", f"+{count_since(90):,}")
    g5.metric("Yearly",    f"+{count_since(365):,}")

    st.markdown("---")
    st.subheader("Trends")

    tab1, tab2, tab3 = st.tabs(["Last 1 month — weekly", "Last 6 months — monthly", "Last 1 year — quarterly"])

    def bar_fig(data, x_col, color=BRAND["primary"]):
        fig = px.bar(data, x=x_col, y="count",
                     labels={x_col: "", "count": "Marketing Contacts"},
                     color_discrete_sequence=[color])
        fig.update_layout(showlegend=False, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        return fig

    with tab1:
        w = df[df["createdate"] >= now - timedelta(days=30)].copy()
        w["week"] = w["createdate"].dt.to_period("W").apply(lambda r: r.start_time.strftime("%d %b"))
        st.plotly_chart(bar_fig(w.groupby("week").size().reset_index(name="count"), "week"), use_container_width=True)

    with tab2:
        m = df[df["createdate"] >= now - timedelta(days=180)].copy()
        m["month"] = m["createdate"].dt.to_period("M").apply(lambda r: r.start_time.strftime("%b %Y"))
        st.plotly_chart(bar_fig(m.groupby("month").size().reset_index(name="count"), "month"), use_container_width=True)

    with tab3:
        q = df.copy()
        q["quarter"] = q["createdate"].dt.to_period("Q").astype(str)
        st.plotly_chart(bar_fig(q.groupby("quarter").size().reset_index(name="count"), "quarter", BRAND["dark"]), use_container_width=True)

    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()
