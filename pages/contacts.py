import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from hubspot_client import get_all_contacts, hesapla_segment, SEGMENT_COLORS, BRAND

def show():
    st.title("Contact Detailed Analysis")
    st.caption(f"Last updated: {datetime.now().strftime('%d %b %Y, %H:%M')}")

    with st.spinner("Loading contacts..."):
        contacts = get_all_contacts()

    if not contacts:
        st.error("No data retrieved.")
        return

    df = pd.DataFrame(contacts)

    for col in ["job_title", "yillik_ciro", "cal_san_say_s_"]:
        if col in df.columns:
            df[col] = df[col].replace({"": None, "None": None, "none": None})

    df["createdate"] = pd.to_numeric(df["createdate"], errors="coerce")
    df["createdate"] = pd.to_datetime(df["createdate"], unit="ms", utc=True, errors="coerce")

    df["segment"] = df.apply(
        lambda r: hesapla_segment(r.get("job_title"), r.get("yillik_ciro"), r.get("cal_san_say_s_"))
        if r.get("hs_marketable_status") == "true" else "Segmentsiz",
        axis=1
    )

    total = len(df)
    now = pd.Timestamp.now(tz="UTC")
    seg_df_all = df[df["segment"] != "Segmentsiz"]
    seg_c = seg_df_all["segment"].value_counts()

    # ── Segment summary ──────────────────────────────────────
    st.subheader("Segment Distribution")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Segmented",  f"{len(seg_df_all):,}", f"{len(seg_df_all)/total*100:.1f}% of total")
    c2.metric("Step Up",    f"{seg_c.get('Step Up',  0):,}")
    c3.metric("Power Up",   f"{seg_c.get('Power Up', 0):,}")
    c4.metric("Scale Up",   f"{seg_c.get('Scale Up', 0):,}")

    # Sadece segmentlenenler, oranlar segment içinde
    seg_plot = seg_df_all["segment"].value_counts().reset_index()
    seg_plot.columns = ["Segment", "Count"]
    seg_plot["Pct"] = (seg_plot["Count"] / len(seg_df_all) * 100).round(1)

    fig_seg = px.bar(
        seg_plot, x="Count", y="Segment", orientation="h",
        color="Segment", color_discrete_map=SEGMENT_COLORS,
        text=seg_plot["Pct"].astype(str) + "%",
    )
    fig_seg.update_layout(showlegend=False, plot_bgcolor="rgba(0,0,0,0)",
                          paper_bgcolor="rgba(0,0,0,0)", xaxis_title="", yaxis_title="",
                          yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig_seg, use_container_width=True)

    st.markdown("---")

    # ── Segment trend ────────────────────────────────────────
    st.subheader("Segment Trend Over Time")
    st.caption("Based on create date — segment distribution of contacts added in each period")

    period_opt = st.selectbox("Period", [
        "Last 1 month — weekly",
        "Last 6 months — monthly",
        "Last 1 year — quarterly",
    ])

    sdf = seg_df_all.copy()
    if period_opt == "Last 1 month — weekly":
        sdf = sdf[sdf["createdate"] >= now - timedelta(days=30)].copy()
        sdf["period"] = sdf["createdate"].dt.to_period("W").apply(lambda r: r.start_time.strftime("%d %b"))
    elif period_opt == "Last 6 months — monthly":
        sdf = sdf[sdf["createdate"] >= now - timedelta(days=180)].copy()
        sdf["period"] = sdf["createdate"].dt.to_period("M").apply(lambda r: r.start_time.strftime("%b %Y"))
    else:
        sdf = sdf[sdf["createdate"] >= now - timedelta(days=365)].copy()
        sdf["period"] = sdf["createdate"].dt.to_period("Q").astype(str)

    if sdf.empty:
        st.info("No segmented contacts in this period.")
    else:
        trend = sdf.groupby(["period", "segment"]).size().reset_index(name="count")
        fig_tr = px.bar(trend, x="period", y="count", color="segment",
                        color_discrete_map=SEGMENT_COLORS, barmode="stack",
                        labels={"period": "", "count": "Contacts", "segment": "Segment"})
        fig_tr.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_tr, use_container_width=True)

    st.markdown("---")

    # ── Field distributions ──────────────────────────────────
    st.subheader("Field Distributions")

    fields = {
        "yillik_ciro":                   "Annual Revenue",
        "cal_san_say_s_":                "Number of Employees",
        "job_title":                     "Job Title",
        "faaliyet_gosterdiginiz_sektor": "Sector",
        "konum":                         "Location",
    }

    for field, label in fields.items():
        if field not in df.columns:
            continue
        fdf = df[df[field].notna() & (df[field] != "")].copy()
        filled = len(fdf)
        st.markdown(f"**{label}** — {filled:,} / {total:,} records filled ({filled/total*100:.1f}%)")

        vc = fdf[field].value_counts().head(10).reset_index()
        vc.columns = ["Value", "Count"]
        vc["Pct"] = (vc["Count"] / filled * 100).round(1)

        col_chart, col_trend = st.columns(2)

        with col_chart:
            fig = px.bar(vc, x="Count", y="Value", orientation="h",
                         text=vc["Pct"].astype(str) + "%",
                         color_discrete_sequence=[BRAND["primary"]])
            fig.update_layout(showlegend=False, plot_bgcolor="rgba(0,0,0,0)",
                              paper_bgcolor="rgba(0,0,0,0)",
                              yaxis=dict(autorange="reversed"),
                              xaxis_title="", yaxis_title="",
                              margin=dict(l=0, r=0, t=10, b=0), height=320)
            st.plotly_chart(fig, use_container_width=True)

        with col_trend:
            cutoff = now - timedelta(days=180)
            tdf = fdf[fdf["createdate"] >= cutoff].copy()
            top_vals = vc["Value"].head(5).tolist()
            tdf_top = tdf[tdf[field].isin(top_vals)]
            if not tdf_top.empty:
                tdf_top = tdf_top.copy()
                tdf_top["month"] = tdf_top["createdate"].dt.to_period("M").apply(
                    lambda r: r.start_time.strftime("%b %Y"))
                td = tdf_top.groupby(["month", field]).size().reset_index(name="count")
                colors = [BRAND["primary"], BRAND["scale_up"], BRAND["blue"], BRAND["secondary"], "#F0991A"]
                fig_t = px.bar(td, x="month", y="count", color=field,
                               barmode="stack", color_discrete_sequence=colors,
                               labels={"month": "", "count": "Contacts", field: ""},
                               title="Last 6 months trend")
                fig_t.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                                    margin=dict(l=0, r=0, t=30, b=0), height=320,
                                    legend=dict(font=dict(size=10)))
                st.plotly_chart(fig_t, use_container_width=True)
            else:
                st.info("Not enough data for trend.")

        st.markdown("---")

    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()
