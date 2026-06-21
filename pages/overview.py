import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from hubspot_client import get_all_contacts, BRAND

def show():
    st.title("General Data Overview")
    st.caption(f"Last updated: {datetime.now().strftime('%d %b %Y, %H:%M')}")

    with st.spinner("Loading contacts..."):
        contacts = get_all_contacts()

    if not contacts:
        st.error("No data retrieved. Please check your HubSpot token.")
        return

    df = pd.DataFrame(contacts)
    df["createdate"] = pd.to_datetime(df["createdate"], errors="coerce")

    total      = len(df)
    marketing  = df[df["hs_marketable_status"] == "true"].shape[0]
    non_mkt    = total - marketing

    # ── Summary ──────────────────────────────────────────────
    st.subheader("Contact Summary")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Contacts",         f"{total:,}")
    c2.metric("Marketing Contacts",     f"{marketing:,}",  f"{marketing/total*100:.1f}% of total")
    c3.metric("Non-Marketing Contacts", f"{non_mkt:,}",    f"{non_mkt/total*100:.1f}% of total")

    # donut
    donut = px.pie(
        values=[marketing, non_mkt],
        names=["Marketing", "Non-Marketing"],
        hole=0.6,
        color_discrete_sequence=[BRAND["primary"], BRAND["light"]],
    )
    donut.update_traces(textinfo="percent+label")
    donut.update_layout(
        showlegend=False,
        margin=dict(t=10, b=10, l=10, r=10),
        height=220,
        paper_bgcolor="rgba(0,0,0,0)",
    )
    _, dc, _ = st.columns([1, 2, 1])
    with dc:
        st.plotly_chart(donut, use_container_width=True)

    st.markdown("---")

    # ── Growth ───────────────────────────────────────────────
    st.subheader("Marketing Contact Growth")
    now = datetime.now(tz=df["createdate"].dt.tz)
    mdf = df[df["hs_marketable_status"] == "true"].copy()

    def count_since(days):
        return mdf[mdf["createdate"] >= now - timedelta(days=days)].shape[0]

    g1, g2, g3, g4, g5 = st.columns(5)
    g1.metric("Daily",     f"+{count_since(1):,}")
    g2.metric("Weekly",    f"+{count_since(7):,}")
    g3.metric("Monthly",   f"+{count_since(30):,}")
    g4.metric("Quarterly", f"+{count_since(90):,}")
    g5.metric("Yearly",    f"+{count_since(365):,}")

    st.markdown("---")

    # ── Trend charts ─────────────────────────────────────────
    st.subheader("Trends")
    tab1, tab2, tab3 = st.tabs(["Last 1 month — weekly", "Last 6 months — monthly", "Last 1 year — quarterly"])

    def bar_fig(df_in, x_col, color=BRAND["primary"]):
        fig = px.bar(df_in, x=x_col, y="count",
                     labels={x_col: "", "count": "Marketing Contacts"},
                     color_discrete_sequence=[color])
        fig.update_layout(showlegend=False,
                          plot_bgcolor="rgba(0,0,0,0)",
                          paper_bgcolor="rgba(0,0,0,0)")
        return fig

    with tab1:
        w = mdf[mdf["createdate"] >= now - timedelta(days=30)].copy()
        w["week"] = w["createdate"].dt.to_period("W").apply(lambda r: r.start_time.strftime("%d %b"))
        st.plotly_chart(bar_fig(w.groupby("week").size().reset_index(name="count"), "week"), use_container_width=True)

    with tab2:
        m = mdf[mdf["createdate"] >= now - timedelta(days=180)].copy()
        m["month"] = m["createdate"].dt.to_period("M").apply(lambda r: r.start_time.strftime("%b %Y"))
        st.plotly_chart(bar_fig(m.groupby("month").size().reset_index(name="count"), "month"), use_container_width=True)

    with tab3:
        q = mdf[mdf["createdate"] >= now - timedelta(days=365)].copy()
        q["quarter"] = q["createdate"].dt.to_period("Q").astype(str)
        st.plotly_chart(bar_fig(q.groupby("quarter").size().reset_index(name="count"), "quarter", BRAND["dark"]), use_container_width=True)

    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()
