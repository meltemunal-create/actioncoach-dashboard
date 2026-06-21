import requests
import streamlit as st
from datetime import datetime, timedelta
import time
import pandas as pd

HUBSPOT_TOKEN = st.secrets["HUBSPOT_TOKEN"]
BASE_URL = "https://api.hubapi.com"
HEADERS = {"Authorization": f"Bearer {HUBSPOT_TOKEN}", "Content-Type": "application/json"}

PROPERTIES = [
    "firstname", "lastname", "email", "createdate",
    "hs_marketable_status",
    "hs_email_optout_176633931",
    "hs_email_hard_bounce_reason_enum",
    "job_title", "yillik_ciro", "cal_san_say_s_",
    "konum", "faaliyet_gosterdiginiz_sektor",
    "hs_analytics_source"
]

BRAND = {
    "primary": "#FF4801", "secondary": "#FFED31",
    "dark": "#202020", "blue": "#0575E5", "light": "#F5F5F5",
    "step_up": "#FF4801", "power_up": "#0575E5", "scale_up": "#7F77DD", "none": "#CCCCCC",
}

SEGMENT_COLORS = {"Step Up": "#FF4801", "Power Up": "#0575E5", "Scale Up": "#7F77DD", "Segmentsiz": "#CCCCCC"}

CHANNEL_COLORS = {
    "ORGANIC_SEARCH": "#FF4801", "DIRECT_TRAFFIC": "#FFED31", "SOCIAL_MEDIA": "#0575E5",
    "EMAIL_MARKETING": "#7F77DD", "PAID_SEARCH": "#F0991A", "PAID_SOCIAL": "#C46B08",
    "REFERRALS": "#FF8C5A", "OTHER_CAMPAIGNS": "#AAAAAA", "OFFLINE": "#888888", "AI_REFERRALS": "#FFD100",
}

CHANNEL_LABELS = {
    "ORGANIC_SEARCH": "Organic Search", "DIRECT_TRAFFIC": "Direct", "SOCIAL_MEDIA": "Social Media",
    "EMAIL_MARKETING": "Email", "PAID_SEARCH": "Paid Search", "PAID_SOCIAL": "Paid Social",
    "REFERRALS": "Referrals", "OTHER_CAMPAIGNS": "Other Campaigns", "OFFLINE": "Offline", "AI_REFERRALS": "AI Referrals",
}

CIRO_PUANI = {
    "0 - 999B": 70, "1M - 4.9M": 70,
    "5M - 24.9M": 140, "25M - 50M": 140,
    "51M - 100M": 210, "101M - 500M": 210, "500M+": 210,
}

CALISAN_PUANI = {
    "1": 30, "2-5": 30, "6-10": 60, "11-25": 60, "26-50": 60, "51-100": 90, "100+": 90,
}

STEP_UP_TITLES = ["Çalışan", "Şu an çalışmıyorum"]

def hesapla_segment(job_title, yillik_ciro, cal_san):
    if pd.isna(job_title) or pd.isna(yillik_ciro) or pd.isna(cal_san):
        return "Segmentsiz"
    if str(job_title).strip() == "" or str(yillik_ciro).strip() == "" or str(cal_san).strip() == "":
        return "Segmentsiz"
    if job_title in STEP_UP_TITLES:
        return "Step Up"
    ciro_p = CIRO_PUANI.get(yillik_ciro, 0)
    cal_p = CALISAN_PUANI.get(cal_san, 0)
    if ciro_p == 0 or cal_p == 0:
        return "Segmentsiz"
    total = ciro_p + cal_p
    if total < 150:
        return "Step Up"
    elif total <= 249:
        return "Power Up"
    else:
        return "Scale Up"

def _req(method, url, max_retries=3, **kwargs):
    for attempt in range(max_retries):
        try:
            resp = requests.request(method, url, **kwargs)
            if resp.status_code in (502, 503, 504):
                time.sleep(2 ** attempt)
                continue
            return resp
        except requests.exceptions.RequestException:
            time.sleep(2 ** attempt)
    return None

def _count(filters):
    resp = _req("POST", f"{BASE_URL}/crm/v3/objects/contacts/search",
                headers=HEADERS, json={"limit": 1, "properties": ["hs_object_id"],
                                       "filterGroups": [{"filters": filters}]})
    return resp.json().get("total", 0) if resp and resp.status_code == 200 else 0

@st.cache_data(ttl=900)
def get_contact_counts():
    resp = _req("POST", f"{BASE_URL}/crm/v3/objects/contacts/search",
                headers=HEADERS, json={"limit": 1, "properties": ["hs_object_id"]})
    total = resp.json().get("total", 0) if resp and resp.status_code == 200 else 0
    marketing    = _count([{"propertyName": "hs_marketable_status", "operator": "EQ", "value": "true"}])
    unsubscribed = _count([{"propertyName": "hs_email_optout_176633931", "operator": "EQ", "value": "true"}])
    bounced      = _count([{"propertyName": "hs_email_hard_bounce_reason_enum", "operator": "HAS_PROPERTY"}])
    return {
        "total": total, "marketing": marketing,
        "non_marketing": total - marketing,
        "unsubscribed": unsubscribed, "bounced": bounced,
    }

@st.cache_data(ttl=900)
def get_marketing_trend():
    contacts = []
    last_id = 0
    cutoff = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    while True:
        body = {
            "limit": 100,
            "properties": ["createdate"],
            "sorts": [{"propertyName": "hs_object_id", "direction": "ASCENDING"}],
            "filterGroups": [{"filters": [
                {"propertyName": "hs_object_id", "operator": "GT", "value": str(last_id)},
                {"propertyName": "createdate", "operator": "GTE", "value": cutoff},
                {"propertyName": "hs_marketable_status", "operator": "EQ", "value": "true"},
            ]}]
        }
        resp = _req("POST", f"{BASE_URL}/crm/v3/objects/contacts/search", headers=HEADERS, json=body)
        if resp is None or resp.status_code != 200:
            break
        data = resp.json()
        results = data.get("results", [])
        if not results:
            break
        for r in results:
            contacts.append(r.get("properties", {}).get("createdate", ""))
        last_id = max(int(r.get("id", 0)) for r in results)
        if len(results) < 100:
            break
        time.sleep(0.05)
    return contacts

@st.cache_data(ttl=900)
def get_all_contacts():
    contacts = []
    vid_offset = 0
    has_more = True
    while has_more:
        resp = _req(
            "GET", f"{BASE_URL}/contacts/v1/lists/all/contacts/all",
            headers=HEADERS,
            params={"count": 100, "vidOffset": vid_offset, "property": PROPERTIES, "showListMemberships": False}
        )
        if resp is None or resp.status_code != 200:
            st.warning("HubSpot geçici olarak yanıt vermiyor, lütfen birkaç dakika sonra sayfayı yenileyin.")
            break
        data = resp.json()
        results = data.get("contacts", [])
        for r in results:
            props_raw = r.get("properties", {})
            contact = {"id": str(r.get("vid", ""))}
            for prop in PROPERTIES:
                val = props_raw.get(prop, {})
                contact[prop] = val.get("value", None) if isinstance(val, dict) else None
            contacts.append(contact)
        has_more = data.get("has-more", False)
        vid_offset = data.get("vid-offset", 0)
        time.sleep(0.05)
    return contacts

@st.cache_data(ttl=900)
def get_all_forms():
    forms = []
    after = None
    while True:
        params = {"limit": 50}
        if after:
            params["after"] = after
        resp = _req("GET", f"{BASE_URL}/marketing/v3/forms", headers=HEADERS, params=params)
        if resp is None or resp.status_code != 200:
            break
        data = resp.json()
        forms.extend(data.get("results", []))
        after = data.get("paging", {}).get("next", {}).get("after")
        if not after:
            break
        time.sleep(0.1)
    return forms

@st.cache_data(ttl=900)
def get_form_submissions(form_id):
    submissions = []
    after = None
    while True:
        params = {"limit": 50}
        if after:
            params["after"] = after
        resp = _req("GET", f"{BASE_URL}/form-integrations/v1/submissions/forms/{form_id}",
                    headers=HEADERS, params=params)
        if resp is None or resp.status_code != 200:
            break
        data = resp.json()
        submissions.extend(data.get("results", []))
        after = data.get("paging", {}).get("next", {}).get("after")
        if not after or len(submissions) > 10000:
            break
        time.sleep(0.1)
    return submissions
