import streamlit as st
import threading
import time

st.set_page_config(
    page_title="ActionCoach Turkey Dashboard",
    page_icon="🔶",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Poppins', sans-serif !important; }
[data-testid="stSidebar"] { background-color: #202020 !important; }
[data-testid="stSidebar"] * { color: #FFFFFF !important; }
[data-testid="stSidebar"] hr { border-color: #444444 !important; }
</style>
""", unsafe_allow_html=True)

def warm_cache():
    while True:
        try:
            from hubspot_client import get_contact_counts, get_marketing_trend, get_all_contacts, get_all_forms
            get_contact_counts()
            get_marketing_trend()
            get_all_contacts()
            get_all_forms()
        except Exception:
            pass
        time.sleep(900)

if "cache_warmer_started" not in st.session_state:
    st.session_state["cache_warmer_started"] = True
    t = threading.Thread(target=warm_cache, daemon=True)
    t.start()

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
