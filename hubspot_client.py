import requests
import streamlit as st
from datetime import datetime, timedelta
import time

HUBSPOT_TOKEN = st.secrets["HUBSPOT_TOKEN"]
BASE_URL = "https://api.hubapi.com"
HEADERS = {"Authorization": f"Bearer {HUBSPOT_TOKEN}", "Content-Type": "application/json"}

PROPERTIES = [
    "firstname", "lastname", "email", "createdate",
    "hs_marketable_status",
    "job_title", "yillik_ciro", "cal_san_say_s_",
    "konum", "faaliyet_gosterdiginiz_sektor",
    "hs_analytics_source"
]

# ---------- BRAND COLORS ----------
BRAND = {
    "primary":   "#FF4801",  # turuncu
    "secondary": "#FFED31",  # sarı
    "dark":      "#202020",  # siyah
    "blue":      "#0575E5",
    "light":     "#F5F5F5",
    "step_up":   "#FF4801",
    "power_up":  "#0575E5",
    "scale_up":  "#202020",
    "none":      "#CCCCCC",
}

SEGMENT_COLORS = {
    "Step Up":     BRAND["step_up"],
    "Power Up":    BRAND["power_up"],
    "Scale Up":    BRAND["dark"],
    "Segmentsiz":  BRAND["none"],
}

CHANNEL_COLORS = {
    "ORGANIC_SEARCH":   "#FF4801",
    "DIRECT_TRAFFIC":   "#FFED31",
    "SOCIAL_MEDIA":     "#0575E5",
    "EMAIL_MARKETING":  "#202020",
    "PAID_SEARCH":      "#F0991A",
    "PAID_SOCIAL":      "#C46B08",
    "REFERRALS":        "#FF8C5A",
    "OTHER_CAMPAIGNS":  "#AAAAAA",
    "OFFLINE":          "#888888",
    "AI_REFERRALS":     "#FFD100",
}

CHANNEL_LABELS = {
    "ORGANIC_SEARCH":   "Organic Search",
    "DIRECT_TRAFFIC":   "Direct",
    "SOCIAL_MEDIA":     "Social Media",
    "EMAIL_MARKETING":  "Email",
    "PAID_SEARCH":      "Paid Search",
    "PAID_SOCIAL":      "Paid Social",
    "REFERRALS":        "Referrals",
    "OTHER_CAMPAIGNS":  "Other Campaigns",
    "OFFLINE":          "Offline",
    "AI_REFERRALS":     "AI Referrals",
}

# ---------- SEGMENT LOGIC ----------
CIRO_PUANI = {
    "0 - 999B": 70, "1M - 4.9M": 70,
    "5M - 24.9M": 140, "25M - 50M": 140,
    "51M - 100M": 210, "101M - 500M": 210, "500M+": 210,
}

CALISAN_PUANI = {
    "1": 30, "2-5": 30,
    "6-10": 60, "11-25": 60, "26-50": 60,
    "51-100": 90, "100+": 90,
}

STEP_UP_TITLES = ["Çalışan", "Şu an çalışmıyorum"]

def hesapla_segment(job_title, yillik_ciro, cal_san):
    if not job_title or not yillik_ciro or not cal_san:
        return "Segmentsiz"
    if job_title in STEP_UP_TITLES:
        return "Step Up"
    ciro_p  = CIRO_PUANI.get(yillik_ciro, 0)
    cal_p   = CALISAN_PUANI.get(cal_san, 0)
    total   = ciro_p + cal_p
    if total < 150:
        return "Step Up"
    elif total <= 249:
        return "Power Up"
    else:
        return "Scale Up"

# ---------- API ----------
@st.cache_data(ttl=900)
def get_all_contacts():
    contacts = []
    after = None
    while True:
        body = {
            "limit": 100,
            "properties": PROPERTIES,
            "sorts": [{"propertyName": "createdate", "direction": "DESCENDING"}],
        }
        if after:
            body["after"] = after
        resp = requests.post(
            f"{BASE_URL}/crm/v3/objects/contacts/search",
            headers=HEADERS,
            json=body,
        )
        if resp.status_code != 200:
            st.error(f"HubSpot API error: {resp.status_code} — {resp.text}")
            break
        data = resp.json()
        for r in data.get("results", []):
            p = r.get("properties", {})
            p["id"] = r.get("id")
            contacts.append(p)
        after = data.get("paging", {}).get("next", {}).get("after")
        if not after:
            break
        time.sleep(0.1)
    return contacts

@st.cache_data(ttl=900)
def get_all_forms():
    resp = requests.get(
        f"{BASE_URL}/marketing/v3/forms",
        headers=HEADERS,
        params={"limit": 50},
    )
    if resp.status_code != 200:
        return []
    return resp.json().get("results", [])

@st.cache_data(ttl=900)
def get_form_submissions(form_id):
    submissions = []
    after = None
    while True:
        params = {"limit": 50}
        if after:
            params["after"] = after
        resp = requests.get(
            f"{BASE_URL}/form-integrations/v1/submissions/forms/{form_id}",
            headers=HEADERS,
            params=params,
        )
        if resp.status_code != 200:
            break
        data = resp.json()
        submissions.extend(data.get("results", []))
        after = data.get("paging", {}).get("next", {}).get("after")
        if not after or len(submissions) > 5000:
            break
        time.sleep(0.1)
    return submissions
