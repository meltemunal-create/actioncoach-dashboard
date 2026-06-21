import streamlit as st

st.set_page_config(
    page_title="ActionCoach Turkey Dashboard",
    page_icon="🔶",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Poppins font + sidebar style
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Poppins', sans-serif !important;
}

[data-testid="stSidebar"] {
    background-color: #202020 !important;
}
[data-testid="stSidebar"] * {
    color: #FFFFFF !important;
}
[data-testid="stSidebar"] .stRadio label {
    color: #FFFFFF !important;
}
[data-testid="stSidebar"] hr {
    border-color: #444444 !important;
}

div[data-testid="metric-container"] > div:first-child {
    color: #888888;
    font-size: 13px;
}
div[data-testid="metric-container"] > div:nth-child(2) {
    color: #202020;
    font-size: 28px;
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)

st.sidebar.image("https://actioncoachturkey.com/wp-content/uploads/2021/01/actioncoach-logo.png", width=160)
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "",
    ["General Data Overview", "Contact Detailed Analysis", "Form Performance"],
)

st.sidebar.markdown("---")
st.sidebar.caption("🔄 Auto-refresh every 15 min")

if page == "General Data Overview":
    from pages.overview import show
    show()
elif page == "Contact Detailed Analysis":
    from pages.contacts import show
    show()
elif page == "Form Performance":
    from pages.forms import show
    show()
