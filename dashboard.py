import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import requests
from io import BytesIO
import json
import os
import sys
import subprocess
import firebase_admin
import streamlit.components.v1 as components
from firebase_admin import credentials, firestore

# --- AUTO-INSTALLER BLOCK ---
# This forces installation into the CURRENT Python environment
try:
    from streamlit_autorefresh import st_autorefresh
except ImportError:
    # If the import fails, install it immediately using the current python executable
    subprocess.check_call([sys.executable, "-m", "pip", "install", "streamlit-autorefresh"])
    from streamlit_autorefresh import st_autorefresh
# ---------------------------

# ================= PAGE CONFIG =================
st.set_page_config(
    page_title="FCR Knits Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 🔄 AUTO-REFRESH: Runs every 15 minutes
st_autorefresh(interval=15 * 60 * 1000, key="datarefresh")
# ================= CONFIGURATION MANAGEMENT =================
# Default URLs (Fallbacks)
DEFAULT_URLS = {
    "ARASIKERE": {
        "dashboard_url": "https://arvindgroup-my.sharepoint.com/:x:/g/personal/gedshirts_consultant_arvind_in/IQDTVZTVcdtOR7ybfN3eIpoIAWe7c7bBJCchZmw2vZNKgqs?e=ghJlMW&download=1",
        "excel_url": "" 
    },
    "RANCHI": {
        "dashboard_url": "https://arvindgroup-my.sharepoint.com/:x:/g/personal/gedshirts_consultant_arvind_in/IQCkdQtFfWX-Q7TFJS4LEm2vAfbJShQrsi48PbatXXJ03Ms?e=eskvlI&download=1",
        "excel_url": "" 
    },
    "INDORE": {
        "dashboard_url": "https://arvindgroup-my.sharepoint.com/:x:/g/personal/gedshirts_consultant_arvind_in/IQCMvYuFTGY5SYl-VS7Fg70AATSU9eGqXevKDKSLc2V-3aI?e=CtZ4A5&download=1",
        "excel_url": ""
    },
    "MATODA": {
        "dashboard_url": "https://arvindgroup-my.sharepoint.com/:x:/g/personal/gedshirts_consultant_arvind_in/IQAPWXjEjFzBSa2tKsCIgXHeAZnDDmdiKwRv4tx15FrsyRM?e=su0DUf&download=1",
        "excel_url": ""
    }
}

@st.cache_resource
def get_db():
    try:
        if not firebase_admin._apps:
            # 1. Try to load from Streamlit Cloud Secrets (for the website)
            if "firebase" in st.secrets:
                key_dict = dict(st.secrets["firebase"])
                cred = credentials.Certificate(key_dict)
            
            # 2. Fallback: Try to load from local file (for your VS Code testing)
            elif os.path.exists("firebase_key.json"):
                cred = credentials.Certificate("firebase_key.json")
            
            else:
                st.error("❌ Firebase Key not found. Please check Secrets on Streamlit Cloud.")
                return None

            firebase_admin.initialize_app(cred)
        return firestore.client()
    except Exception as e:
        st.error(f"Firebase Error: {e}")
        return None

def load_config():
    """Load URLs from Firebase Firestore."""
    try:
        db = get_db()
        if db:
            doc_ref = db.collection("settings").document("unit_config")
            doc = doc_ref.get()
            if doc.exists:
                return doc.to_dict()
            else:
                save_config(DEFAULT_URLS)
                return DEFAULT_URLS
    except Exception:
        return DEFAULT_URLS
    return DEFAULT_URLS

def save_config(data):
    """Save URLs to Firebase Firestore."""
    try:
        db = get_db()
        if db:
            doc_ref = db.collection("settings").document("unit_config")
            doc_ref.set(data)
    except Exception:
        pass

# Initialize Session State
if 'admin_logged_in' not in st.session_state:
    st.session_state.admin_logged_in = False
if 'show_login' not in st.session_state:
    st.session_state.show_login = False

if 'show_summary' not in st.session_state:
    st.session_state.show_summary = False

# ================= CUSTOM CSS =================
st.markdown("""
<style>
/* ================= Global Cleanups ================= */
div.block-container { padding-top: 1rem; padding-bottom: 2rem; }
header[data-testid="stHeader"] { display: none; }

/* 🔥 BACKGROUND THEME */
.stApp { 
    background: linear-gradient(135deg, #f0f9ff 0%, #bae6fd 100%); 
}

/* ================= FILTER STYLING ================= */
.stMultiSelect label, .stSelectbox label, .stTextInput label {
    color: #0c4a6e !important;
    font-weight: 800 !important;
    font-size: 15px !important;
}

div[data-baseweb="select"] > div, div[data-baseweb="input"] > div {
    background: linear-gradient(180deg, #ffffff 0%, #e0f2fe 100%) !important;
    border: 2px solid #38bdf8 !important;
    border-radius: 12px !important;
    color: #0284c7 !important;
}

/* ================= Top Ribbon ================= */
.top-ribbon {
    background: linear-gradient(90deg, #0284c7, #0ea5e9, #22d3ee);
    border-radius: 20px;
    padding: 18px 26px;
    box-shadow: 0 10px 25px rgba(14, 165, 233, 0.3);
    margin-bottom: 15px;
    z-index: 1;
}
.ribbon-header { color:white; }
.ribbon-title { font-size: 32px; font-weight: 800; }
.ribbon-time { font-size: 14px; opacity: 0.9; margin-top: 5px; font-weight: 500; }

/* ================= NEW GROUP CARD STYLING ================= */
.group-card {
    background: #ffffff;
    border-radius: 16px;
    padding: 20px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    border: 2px solid #38bdf8; 
    height: 100%;
    transition: all 0.3s ease;
}

/* 🔥 ALERT ANIMATION KEYFRAMES (RED GLOW) */
@keyframes flashRed {
    0% { border-color: #38bdf8; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    50% { border-color: #dc2626; box-shadow: 0 0 15px rgba(220, 38, 38, 0.6); } /* Red Glow */
    100% { border-color: #38bdf8; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
}

/* Class to trigger the animation */
.alert-card {
    /* Runs 3 TIMES (1s each cycle = 3s total duration) */
    animation: flashRed 1s ease-in-out 3; 
}

.group-header {
    font-size: 18px;
    font-weight: 800;
    color: #0c4a6e; /* Dark Blue Header */
    text-transform: uppercase;
    border-bottom: 2px solid #f1f5f9;
    padding-bottom: 10px;
    margin-bottom: 15px;
    letter-spacing: 0.5px;
    text-align: center;
}

.metric-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 1px dashed #f1f5f9;
    position: relative; /* For tooltip positioning */
}
.metric-row:last-child {
    border-bottom: none;
    margin-bottom: 0;
}

.m-label {
    font-size: 14px;
    font-weight: 600;
    color: #64748b; /* Slate Gray */
}

.m-value {
    font-size: 18px;
    font-weight: 800;
    text-align: right;
}

/* ================= GRAPH STYLING ================= */
.stPlotlyChart {
    background: #ffffff !important;
    border-radius: 20px !important;
    border: 2px solid #000000 !important;
    box-shadow: 0 4px 12px rgba(0,0,0,0.05) !important;
    overflow: hidden;
    padding: 10px;
}

/* ================= Exception Cards ================= */
.exception-card-container {
    border-radius: 16px; height: 75px; display: flex; flex-direction: column;
    justify-content: center; align-items: center; text-align: center;
    box-shadow: 0 4px 10px rgba(0,0,0,0.1); margin-bottom: -75px; z-index: 0;
}
.ex-lbl { font-size: 12px; font-weight: 600; text-transform: uppercase; color:white; }
.ex-val { font-size: 24px; font-weight: 800; color:white; }

.bg-indigo { background: linear-gradient(135deg, #2563eb, #60a5fa); }
.bg-cyan   { background: linear-gradient(135deg, #0891b2, #22d3ee); }
.bg-green  { background: linear-gradient(135deg, #059669, #34d399); }

/* ================= Info Button ================= */
.info-btn-css button {
    background-color: #ffffff !important; border: none !important; color: #0ea5e9 !important;
    border-radius: 50% !important; width: 35px !important; height: 35px !important;
    position: relative; left: 88%; top: 20px; z-index: 10;
}
.spacer-area { height: 10px; }

/* ================= Standard Buttons ================= */
div.stButton > button {
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%) !important;
    color: white !important;
    border: 2px solid #38bdf8 !important;
    border-radius: 10px !important;
}

/* ================= Admin Login Styles ================= */
.admin-box {
    background-color: white;
    padding: 30px;
    border-radius: 20px;
    border: 2px solid #38bdf8;
    box-shadow: 0 10px 30px rgba(0,0,0,0.1);
    max-width: 500px;
    margin: auto;
}
</style>
""", unsafe_allow_html=True)

# ================= DATA LOADER =================
@st.cache_data(ttl=300)
def load_data(url):
    try:
        r = requests.get(url)
        r.raise_for_status()
        df = pd.read_excel(BytesIO(r.content), engine="openpyxl")
        
        num_cols = ['ORD QTY','CAN CUT QTY','CUT QTY','FAB Req','FAB RCVD', 'FABRIC USED',
                    'FABRIC LEFTOVER STOCK','STD Cons','CAD Cons',
                    'ACHIEVED CONS','CAN CUT %','CUT %']
        for c in num_cols:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

        if 'END DATE' in df.columns:
            df['END DATE'] = pd.to_datetime(df['END DATE'], errors='coerce', dayfirst=True)
            df['MONTH_STR'] = df['END DATE'].dt.strftime('%b-%y').str.upper().fillna("N/A")
        else:
            df['MONTH_STR'] = "N/A"
        return df
    except Exception as e:
        return pd.DataFrame()

# ================= ADMIN LOGIC FUNCTIONS =================
def login_callback():
    if st.session_state.username == "admin" and st.session_state.password == "123456":
        st.session_state.admin_logged_in = True
        st.session_state.show_login = False
    else:
        st.error("❌ Invalid Credentials")

def logout_callback():
    st.session_state.admin_logged_in = False
    st.session_state.show_login = False

def toggle_login():
    st.session_state.show_login = not st.session_state.show_login

# ================= LAYOUT LOGIC =================

# 1. Load Configuration
UNIT_URLS = load_config()

if 'selected_months_memory' not in st.session_state:
    # This runs ONLY on the first page load or full browser refresh
    now = datetime.now()
    if now.day <= 10:
        target_date = now.replace(day=1) - timedelta(days=1)
    else:
        target_date = now
    
    # Store the default month based on your original logic
    st.session_state['selected_months_memory'] = [target_date.strftime('%b-%y').upper()]

# 2. Layout Structure
if st.session_state.admin_logged_in:
    # ------------------ ADMIN PANEL VIEW ------------------
    st.markdown("<h1 style='text-align: center; color: #0c4a6e;'>⚙️ Admin Panel - Link Manager (Firebase)</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'><b>Dashboard Link:</b> The direct download link used by this app.<br><b>Excel Link:</b> Store your original Excel location here for future reference.</p>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    with st.container():
        c_adm1, c_adm2, c_adm3 = st.columns([0.5, 4, 0.5])
        with c_adm2:
            with st.form("admin_link_form"):
                new_config = {}
                for unit, details in UNIT_URLS.items():
                    st.markdown(f"### 📂 {unit}")
                    
                    # Safe get
                    d_val = details.get("dashboard_url", "") if isinstance(details, dict) else str(details)
                    e_val = details.get("excel_url", "") if isinstance(details, dict) else ""
                    
                    col_d, col_e = st.columns(2)
                    with col_d:
                        d_new = st.text_input("Dashboard Link (Direct)", value=d_val, key=f"{unit}_d")
                    with col_e:
                        e_new = st.text_input("Original Excel Link (Reference)", value=e_val, key=f"{unit}_e")
                    
                    st.markdown("<hr style='margin: 5px 0 15px 0;'>", unsafe_allow_html=True)
                    new_config[unit] = {"dashboard_url": d_new, "excel_url": e_new}
                
                submitted = st.form_submit_button("💾 Save to Cloud", use_container_width=True)
                
                if submitted:
                    save_config(new_config)
                    st.cache_data.clear() 
                    st.success("✅ Links saved to Firebase! These are now permanent.")

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("⬅️ Logout & Return to Dashboard", use_container_width=True):
                logout_callback()
                st.rerun()

elif st.session_state.show_login:
    # ------------------ LOGIN POPUP VIEW ------------------
    st.markdown("<br><br>", unsafe_allow_html=True)
    c_log1, c_log2, c_log3 = st.columns([1, 1, 1])
    with c_log2:
        st.markdown("""
        <div class="admin-box">
            <h2 style='text-align: center; color: #0c4a6e; margin-bottom: 20px;'>🔐 Admin Login</h2>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("login_form"):
            st.text_input("Username", key="username")
            st.text_input("Password", type="password", key="password")
            st.form_submit_button("Login", on_click=login_callback, use_container_width=True)
            
        if st.button("Cancel", use_container_width=True):
            toggle_login()
            st.rerun()

else:
    # ------------------ MAIN DASHBOARD VIEW ------------------
    if 'active_exception_view' not in st.session_state:
        st.session_state.active_exception_view = None

    now_dt = datetime.now()
    now_str = now_dt.strftime("%d-%b-%Y %I:%M %p")

    # ================= HEADER LAYOUT =================
    c_header, c_unit, c_gear = st.columns([5.5, 2, 0.5], gap="small")

    # 1. EXECUTE UNIT SELECTOR FIRST
    with c_unit:
        selected_unit = st.selectbox("🏭 Select Unit", list(UNIT_URLS.keys()), index=0)

    # 2. EXECUTE GEAR BUTTON
    with c_gear:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        if st.button("⚙️", key="admin_gear_btn", help="Admin Login"):
            toggle_login()
            st.rerun()

    # 3. EXECUTE HEADER TITLE LAST
    with c_header:
        st.markdown(f"""
        <div class="top-ribbon">
            <div class="ribbon-header">
                <div class="ribbon-title">FCR KNITS - {selected_unit}</div>
                <div class="ribbon-time">Last Refreshed: {now_str}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Load Data
    config_entry = UNIT_URLS.get(selected_unit, {})
    if isinstance(config_entry, dict):
        data_url = config_entry.get("dashboard_url", "")
    else:
        data_url = str(config_entry)

    df = load_data(data_url)

    # ... REST OF YOUR DASHBOARD LOGIC ...
    if not df.empty:
        with st.container():
            st.markdown('<div class="ribbon-filters">', unsafe_allow_html=True)
            f1,f2,f3,f4,f5 = st.columns([1,1,1,1,0.6])
            
            with f1:
                # 1. Get unique months from data
                raw_months = [str(m) for m in df['MONTH_STR'].unique() if str(m) != 'nan' and m != "N/A"]
                
                # 2. Sort months in DESCENDING chronological order
                # We convert "JAN-26" to a date object to sort correctly, then back to the string
                month_options = sorted(
                    raw_months, 
                    key=lambda x: datetime.strptime(x, '%b-%y'), 
                    reverse=True
                )
                
                # 3. Set INITIAL logic only if nothing has been selected yet
                if 'month_memory' not in st.session_state:
                    if now_dt.day <= 10:
                        target_date = now_dt.replace(day=1) - timedelta(days=1)
                    else:
                        target_date = now_dt
                    initial_val = target_date.strftime('%b-%y').upper()
                    st.session_state.month_memory = [initial_val] if initial_val in month_options else []

                # 4. Filter memory to ensure only months existing in the current Unit are used
                valid_selections = [m for m in st.session_state.month_memory if m in month_options]

                # 5. The Multiselect Widget with the sorted descending options
                sel_month = st.multiselect(
                    "📅 Month", 
                    options=month_options, 
                    default=valid_selections, 
                    placeholder="All Months",
                    key="month_selector"
                )
                
                # Update memory
                st.session_state.month_memory = sel_month
            
            dff = df[df['MONTH_STR'].isin(sel_month)] if sel_month else df
            
        

            with f2:
                buyer_options = sorted([str(b) for b in dff['BUYER'].unique() if str(b) != 'nan'])
                sel_buyer = st.multiselect("👤 Buyer", buyer_options, default=[], placeholder="All Buyers")
            
            dff = dff[dff['BUYER'].astype(str).isin(sel_buyer)] if sel_buyer else dff

            with f3:
                status_options = sorted([str(s) for s in dff['STATUS'].unique() if str(s) != 'nan'])
                s_default = ["Completed"] if "Completed" in status_options else []
                sel_status = st.multiselect("📌 Status", status_options, default=s_default, placeholder="All Status")
            
            dff = dff[dff['STATUS'].astype(str).isin(sel_status)] if sel_status else dff

            with f4:
                style_options = sorted([str(st_no) for st_no in dff['STYLE NO'].unique() if str(st_no) != 'nan'])
                sel_style = st.multiselect("👕 Style", style_options, default=[], placeholder="All Styles")
            
            dff = dff[dff['STYLE NO'].astype(str).isin(sel_style)] if sel_style else dff

            with f5:
                st.markdown("<div style='height:35px'></div>", unsafe_allow_html=True)
                
                # Button 1: Refresh
                if st.button("🔄 Refresh", use_container_width=True):
                    st.cache_data.clear()
                    st.session_state.active_exception_view = None
                    st.rerun()

                

        # Calculations
        sum_cut = dff['CUT QTY'].sum()
        sum_cancut = dff['CAN CUT QTY'].sum()
        sum_ord = dff['ORD QTY'].sum()
        sum_req = dff['FAB Req'].sum()
        sum_rcvd = dff['FAB RCVD'].sum()
        sum_used = dff['FABRIC USED'].sum() if 'FABRIC USED' in dff.columns else 0
        sum_stock = dff['FABRIC LEFTOVER STOCK'].sum()
        
        # Weighted/Total Based Formulas
        # 1. STD Cons: (Sum of FAB Req) / (Sum of ORD QTY)
        avg_std = (sum_req / sum_ord) if sum_ord > 0 else 0

        # 2. CAD Cons: Sum of (CAD Cons * ORD QTY) / Sum of ORD QTY
        # We calculate row-wise multiplication first, then sum
        cad_weighted_sum = (dff['CAD Cons'] * dff['ORD QTY']).sum()
        avg_cad = (cad_weighted_sum / sum_ord) if sum_ord > 0 else 0

        # 3. Factory Achieved Cons: (Sum of FABRIC USED) / (Sum of CUT QTY)
        avg_ach = (sum_used / sum_cut) if sum_cut > 0 else 0

        # (Keep these as they were or adjust if needed)
        avg_cancut_p = dff['CAN CUT %'].mean()*100 if not dff.empty else 0
        avg_cut_p = dff['CUT %'].mean()*100 if not dff.empty else 0

        perf_cut = (sum_cut/sum_cancut*100) if sum_cancut>0 else 0
        perf_rcvd = (sum_rcvd/sum_req*100) if sum_req>0 else 0
        perf_cons = avg_ach-avg_std

        ex1_count = len(dff[dff['CUT %'] < 1])
        ex2_count = len(dff[(dff['CAN CUT %'] < 1.01) & (dff['CUT %'] < 1.01)]) # Updated
        ex3_count = len(dff[(dff['CUT %'] < dff['CAN CUT %']) & (dff['CUT %'] < 1.01)]) # Updated
        
        def fmt(v): return str(v) if v>0 else "--"

        # Color Text Constants
        txt_green = "#16a34a" # Emerald Green
        txt_red = "#dc2626"   # Red
        txt_amber = "#d97706" # Amber
        txt_black = "#1e293b" # Dark Blue/Black
        
        # --- Logic for Text Colors ---
        # Quantity
        cp_color = txt_green if perf_cut >= 100 else txt_red
        ord_color = txt_green 
        cc_color = txt_green if avg_cancut_p > 100 else (txt_amber if avg_cancut_p == 100 else txt_red)
        cut_color = txt_green if avg_cut_p >= avg_cancut_p else txt_red

        # Fabric
        req_color = txt_black
        rcvd_color = txt_green if sum_rcvd >= sum_req else txt_red
        used_color = txt_black
        stock_color = txt_green if sum_stock >= 0 else txt_red

        # Consumption
        std_color = txt_black
        cad_color = txt_green if avg_cad <= avg_std else txt_red
        ach_color = txt_green if avg_ach <= avg_std else txt_red
        cons_color = txt_red if perf_cons > 0 else txt_green

        # --- ALERT FLAGS (Trigger if ANY value in the card is RED) ---
        # Checks if any of the text colors assigned to the metrics equal the red constant
        alert_qty = (cp_color == txt_red) or (cc_color == txt_red) or (cut_color == txt_red)
        alert_fab = (rcvd_color == txt_red) or (stock_color == txt_red)
        alert_cons = (cad_color == txt_red) or (ach_color == txt_red) or (cons_color == txt_red)

        # Helper to Render Group Card
        def render_group_card(title, metrics, alert_trigger=False):
            # metrics is list of tuples: (label, value_str, color_hex, tooltip_text)
            rows_html = ""
            for lbl, val, col, tooltip in metrics:
                # Added 'title' attribute for hover tooltip
                rows_html += f'<div class="metric-row" title="{tooltip}"><span class="m-label">{lbl}</span><span class="m-value" style="color: {col};">{val}</span></div>'
            
            # If alert_trigger is True, add the 'alert-card' class
            card_class = "group-card alert-card" if alert_trigger else "group-card"
            
            st.markdown(f"""
            <div class="{card_class}">
                <div class="group-header">{title}</div>
                {rows_html}
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<div style='height:15px'></div>", unsafe_allow_html=True)

        # === NEW LAYOUT: 3 BIG CARDS IN ONE ROW ===
        c_qty, c_fab, c_cons = st.columns(3)

        with c_qty:
            render_group_card("Quantity", [
                ("Can Cut Performance", f"{perf_cut:,.2f}%", cp_color, "Formula: (Total Cut Qty / Total Can Cut Qty) * 100"),
                ("Order Qty", f"{sum_ord:,.0f}", ord_color, "Total Order Quantity of selected filters"),
                ("Can Cut Qty", f"{sum_cancut:,.0f} ({avg_cancut_p:.2f}%)", cc_color, "Total Quantity feasible to cut based on Fabric Availability"),
                ("Cut Qty", f"{sum_cut:,.0f} ({avg_cut_p:.2f}%)", cut_color, "Total Actual Cut Quantity produced")
            ], alert_trigger=alert_qty)

        with c_fab:
            render_group_card("Fabric", [
                ("Fabric Required", f"{sum_req:,.2f}", req_color, "Total Fabric Required for orders"),
                ("Fabric Received", f"{sum_rcvd:,.2f} ({perf_rcvd:.2f}%)", rcvd_color, "Total Fabric Received from store (Percentage of Required)"),
                ("Fabric Used", f"{sum_used:,.2f}", used_color, "Total Fabric consumed in cutting"),
                ("Fabric Leftover", f"{sum_stock:,.2f}", stock_color, "Fabric Remaining Stock (Received - Used)")
            ], alert_trigger=alert_fab)

        with c_cons:
            sym = "+" if perf_cons > 0 else ""
            render_group_card("Consumption", [
                ("STD Cons", f"{avg_std:.3f}", std_color, "Average Standard Consumption (Budgeted)"),
                ("CAD Cons", f"{avg_cad:.3f}", cad_color, "Average CAD Consumption (Marker Plan)"),
                ("Factory Achieved Cons", f"{avg_ach:.3f}", ach_color, "Average Actual Consumption on Floor"),
                ("Cons Performance", f"{sym}{perf_cons:.3f}", cons_color, "Difference: Achieved Cons - STD Cons (Positive means excess usage)")
            ], alert_trigger=alert_cons)

        st.markdown("<div style='height:25px'></div>", unsafe_allow_html=True)

        # Exception & Chart
        c1, c2 = st.columns([1, 2])
        with c1:
            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
            def render_centered_card(bg_class, title, count, btn_key, view_id):
                st.markdown(f'<div class="exception-card-container {bg_class}"><div class="ex-text-group"><div class="ex-lbl">{title}</div><div class="ex-val">{count}</div></div></div>', unsafe_allow_html=True)
                st.markdown('<div class="info-btn-css">', unsafe_allow_html=True)
                if st.button("ⓘ", key=btn_key): st.session_state.active_exception_view = view_id
                st.markdown('</div><div class="spacer-area"></div>', unsafe_allow_html=True)

            render_centered_card("bg-indigo", "CUT% < 100%", fmt(ex1_count), "btn_ex1", "ex1")
            render_centered_card("bg-cyan", "CAN CUT% < 101%", fmt(ex2_count), "btn_ex2", "ex2")
            render_centered_card("bg-green", "CUT% < CAN CUT%", fmt(ex3_count), "btn_ex3", "ex3")
            
            # --- SUMMARY BUTTON ---
            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
            if st.button("📋 View All Units Summary", use_container_width=True):
                st.session_state.show_summary = True

        with c2:
            if 'BUYER' in dff.columns and not dff.empty:
                # 1. Faster Aggregation
                dfc = dff.groupby('BUYER').agg({
                    'CAN CUT %': 'mean',
                    'CUT %': 'mean'
                }).reset_index()
                
                dfc['CAN CUT %'] *= 100
                dfc['CUT %'] *= 100
                dfc = dfc.sort_values(by='CAN CUT %', ascending=False)

                fig = go.Figure()
                
                # 2. Optimized Bar Traces
                fig.add_trace(go.Bar(
                    x=dfc['BUYER'], y=dfc['CAN CUT %'], name="Can Cut %", 
                    marker=dict(color="#2c6e9e"),
                    text=[f"{v:.1f}%" for v in dfc['CAN CUT %']], textposition="auto",
                    marker_cornerradius=10
                ))
                
                fig.add_trace(go.Bar(
                    x=dfc['BUYER'], y=dfc['CUT %'], name="Cut %", 
                    marker=dict(color="#5fa6e1"),
                    text=[f"{v:.1f}%" for v in dfc['CUT %']], textposition="auto",
                    marker_cornerradius=10
                ))

                fig.add_trace(go.Scatter(
                    x=dfc['BUYER'], y=dfc['CUT %'], mode='lines+markers', name='Trend',
                    line=dict(color="#e11d48", width=3),
                    marker=dict(size=8, color="#e11d48"),
                    showlegend=False
                ))

                fig.update_layout(
                    title=dict(
                        text="📈 Performance by Buyer", 
                        font=dict(size=22, color="#1e293b", weight=700),
                        x=0.01 # Aligns title to the left
                    ),
                    hovermode="x unified", 
                    barmode='group', 
                    height=400,
                    # --- INCREASED MARGINS ---
                    # Increasing 'r' (right) from 10 to 40 prevents clipping
                    margin=dict(l=20, r=40, t=60, b=20), 
                    showlegend=True,
                    # --- ADJUSTED LEGEND ---
                    # Setting x to 0.98 instead of 1.0 pulls it away from the edge
                    legend=dict(
                        orientation="h", 
                        yanchor="bottom", 
                        y=1.02, 
                        xanchor="right", 
                        x=0.98 
                    ),
                    yaxis=dict(showgrid=True, gridcolor='#f1f5f9'),
                    xaxis=dict(showgrid=False)
                )

                # 3. Use 'use_container_width=True' and turn off 'displaylogo'
                st.plotly_chart(fig, use_container_width=True, config={'displaylogo': False, 'staticPlot': False})
            else:
                st.info("No data available for the selected filters.")

        # Detail Table
        if st.session_state.active_exception_view:
            st.markdown("---")
            st.markdown('<div id="summary_target"></div>', unsafe_allow_html=True)
            components.html(
                """
                <script>
                    window.parent.document.getElementById("summary_target").scrollIntoView({behavior: "smooth", block: "start"});
                </script>
                """,
                height=0,
                width=0
            )
            detail_df = pd.DataFrame()
            view_title = ""
            view_color = ""

            if st.session_state.active_exception_view == 'ex1':
                detail_df = dff[dff['CUT %'] < 1].copy()
                view_title = "🚨 Orders with CUT % < 100%"
                view_color = "#6366f1"
            elif st.session_state.active_exception_view == 'ex2':
                # This filter now ensures you only see rows where both percentages are under 101%
                detail_df = dff[(dff['CAN CUT %'] < 1.01) & (dff['CUT %'] < 1.01)].copy() 
                view_title = "⚠️ Orders with CAN CUT % < 101% (Excl. Cut >101%)"
                view_color = "#06b6d4"
            elif st.session_state.active_exception_view == 'ex3':
                # Updated filter to exclude anything where CUT % is 101% or higher
                detail_df = dff[(dff['CUT %'] < dff['CAN CUT %']) & (dff['CUT %'] < 1.01)].copy()
                view_title = "📉 Orders where CUT % < CAN CUT % (Excl. >101%)"
                view_color = "#10b981"

            if not detail_df.empty:
                detail_df.reset_index(drop=True, inplace=True)
                detail_df.insert(0, 'SL. NO.', range(1, 1 + len(detail_df)))

            disp_cols = ['SL. NO.', 'BUYER', 'STYLE NO', 'COLOUR', 'ORD QTY', 'CAN CUT %', 'CUT %', 'FABRIC LEFTOVER STOCK', 'REMARKS']
            final_cols = [c for c in disp_cols if c in detail_df.columns]

            h1, h2 = st.columns([4, 1])
            with h1:
                st.markdown(f"<h3 style='color:{view_color};'>{view_title} ({len(detail_df)} Records)</h3>", unsafe_allow_html=True)
            with h2:
                if st.button("❌ Close Details", use_container_width=True):
                    st.session_state.active_exception_view = None
                    st.rerun()

            if not detail_df.empty:
                def color_red_if_low(val):
                    if isinstance(val, (int, float)) and val < 1.0:
                        return 'color: #dc2626; font-weight: bold;'
                    return ''

                styled_df = detail_df[final_cols].style.format({
                    'SL. NO.': '{:.0f}',
                    'ORD QTY': '{:,.0f}',
                    'FABRIC LEFTOVER STOCK': '{:,.2f}',
                    'CAN CUT %': '{:.2%}',
                    'CUT %': '{:.2%}'
                })\
                .map(color_red_if_low, subset=['CAN CUT %', 'CUT %'])\
                .set_properties(**{'background-color': '#f8fafc', 'color': '#000080', 'border-color': '#cbd5e1'})

                st.dataframe(
                    styled_df, use_container_width=True, height=400, hide_index=True,
                    column_config={
                        "SL. NO.": st.column_config.NumberColumn("SL. NO.", width="small"),
                        "REMARKS": st.column_config.TextColumn("Remarks", width="large"),
                        "STYLE NO": st.column_config.TextColumn("Style No", width="medium"),
                    }
                )
            else:
                st.success("✅ No exceptions found!")

        # ----------------------------------------------------------------
        # 🔥 GLOBAL SUMMARY TABLE (WITH STATUS FILTER)
        # ----------------------------------------------------------------
        if st.session_state.show_summary:
            st.markdown("---")
            st.markdown('<div id="summary_target"></div>', unsafe_allow_html=True)
            components.html(
                """
                <script>
                    window.parent.document.getElementById("summary_target").scrollIntoView({behavior: "smooth", block: "start"});
                </script>
                """,
                height=0,
                width=0
            )
            st.subheader("🌍 All Units Summary Report")
            
            with st.spinner("Compiling data from all units..."):
                all_units_data = {}
                all_months = set()
                
                # 1. FIRST PASS: Load all data and identify available Months
                for unit_name, config in UNIT_URLS.items():
                    u_url = config.get("dashboard_url", "") if isinstance(config, dict) else str(config)
                    u_df = load_data(u_url)
                    
                    if not u_df.empty:
                        # Ensure END DATE is datetime and create Week/Month strings from it
                        u_df['END DATE'] = pd.to_datetime(u_df['END DATE'], errors='coerce')
                        u_df['MONTH_STR'] = u_df['END DATE'].dt.strftime('%b-%y').str.upper()
                        # Create Week string directly from END DATE (e.g., WK01, WK52)
                        u_df['WEEK_FMT'] = u_df['END DATE'].dt.isocalendar().week.apply(lambda x: f"WK{int(x):02d}" if pd.notnull(x) else "N/A")
                        
                        all_units_data[unit_name] = u_df
                        all_months.update(u_df['MONTH_STR'].dropna().unique())

                # 2. RENDER MONTH FILTER FIRST
                sf1, sf2, sf3 = st.columns(3)
                
                # --- NEW DEFAULT MONTH LOGIC ---
                now = datetime.now()
                # If today is the 1st week (Day 1 to 7), target the previous month
                if now.day <= 7:
                    # Move to the 1st of this month, then subtract 1 day to get the previous month
                    target_date = now.replace(day=1) - timedelta(days=1)
                else:
                    # Otherwise, target the current month
                    target_date = now
                
                # Format to match your data (e.g., "DEC-25")
                default_month_str = target_date.strftime('%b-%y').upper()
                # -------------------------------

                with sf1:
                    summ_sel_month = st.multiselect(
                        "1. Select Month(s)", 
                        sorted(list(all_months)), 
                        default=[default_month_str] if default_month_str in all_months else []
                    )

                # 3. SECOND PASS: Identify weeks ONLY for the selected months
                available_weeks = set()
                for u_df in all_units_data.values():
                    filtered_by_month = u_df[u_df['MONTH_STR'].isin(summ_sel_month)] if summ_sel_month else u_df
                    available_weeks.update(filtered_by_month['WEEK_FMT'].unique())
                
                if "N/A" in available_weeks: available_weeks.remove("N/A")

                # 4. RENDER WEEK & STATUS FILTERS (Now dependent on Month)
                with sf2:
                    sorted_weeks = sorted(list(available_weeks))
                    summ_sel_week = st.multiselect("2. Select Week(s)", sorted_weeks, placeholder="All weeks in selected month")
                
                # Get statuses for the selected month/week
                all_statuses = set()
                for u_df in all_units_data.values():
                    temp = u_df[u_df['MONTH_STR'].isin(summ_sel_month)] if summ_sel_month else u_df
                    if summ_sel_week:
                        temp = temp[temp['WEEK_FMT'].isin(summ_sel_week)]
                    all_statuses.update(temp['STATUS'].dropna().unique())

                with sf3:
                    summ_sel_status = st.multiselect("3. Select Status", sorted(list(all_statuses)), default=["Completed"] if "Completed" in all_statuses else [])

                # 4. AGGREGATE DATA
                # 5. FINAL AGGREGATION
                summary_rows = []
                for unit_name, u_df in all_units_data.items():
                    temp_df = u_df.copy()
                    
                    # Apply the dynamic filters
                    if summ_sel_month:
                        temp_df = temp_df[temp_df['MONTH_STR'].isin(summ_sel_month)]
                    if summ_sel_week:
                        temp_df = temp_df[temp_df['WEEK_FMT'].isin(summ_sel_week)]
                    if summ_sel_status:
                        temp_df = temp_df[temp_df['STATUS'].isin(summ_sel_status)]
                    
                    if not temp_df.empty:
                        # (Keep your existing weighted calculation logic here)
                        s_ord = temp_df['ORD QTY'].sum()
                        s_req = temp_df['FAB Req'].sum()
                        
                        summary_rows.append({
                            "UNIT NAME": unit_name,
                            "ORD QTY": s_ord,
                            "STD Cons": (s_req / s_ord) if s_ord > 0 else 0,
                            "CAD Cons": ((temp_df['CAD Cons'] * temp_df['ORD QTY']).sum() / s_ord) if s_ord > 0 else 0,
                            "CAN CUT %": temp_df['CAN CUT %'].mean(), 
                            "CUT %": temp_df['CUT %'].mean(),
                            "LEFTOVER STOCK": temp_df['FABRIC LEFTOVER STOCK'].sum()
                        })

                # 5. DISPLAY TABLE (Light Blue Style)
                if summary_rows:
                    summ_df = pd.DataFrame(summary_rows)
                    
                    styled_summ = summ_df.style.format({
                        "ORD QTY": "{:,.0f}",
                        "STD Cons": "{:.3f}",
                        "CAD Cons": "{:.3f}",
                        "CAN CUT %": "{:.2%}",
                        "CUT %": "{:.2%}",
                        "LEFTOVER STOCK": "{:,.2f}"
                    }).set_properties(**{
                        'background-color': '#e0f2fe',  # Light Blue
                        'color': '#0c4a6e',             # Dark Blue Text
                        'border-color': '#ffffff'
                    })

                    st.dataframe(styled_summ, use_container_width=True, hide_index=True)
                else:
                    st.warning("⚠️ No data matches the selected filters.")

            if st.button("❌ Close Summary", key="close_summ_btn"):
                st.session_state.show_summary = False
                st.rerun()
