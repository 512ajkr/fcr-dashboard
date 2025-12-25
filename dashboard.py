import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import requests
from io import BytesIO
import json
import os
import firebase_admin
from firebase_admin import credentials, firestore

# ================= PAGE CONFIG =================
st.set_page_config(
    page_title="FCR Knits Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ================= FIREBASE CONNECTION =================
def get_db():
    """Connect to Firebase securely using Streamlit Secrets."""
    if not firebase_admin._apps:
        # Check if secrets are available
        if "firebase" in st.secrets:
            # Create a dictionary from secrets and fix the newlines in private key
            key_dict = dict(st.secrets["firebase"])
            key_dict["private_key"] = key_dict["private_key"].replace("\\n", "\n")
            
            cred = credentials.Certificate(key_dict)
            firebase_admin.initialize_app(cred)
        else:
            st.error("❌ Firebase Credentials missing! Please add [firebase] to .streamlit/secrets.toml")
            return None
    return firestore.client()

# ================= CONFIGURATION MANAGEMENT (FIREBASE) =================
# Default URLs (Fallbacks used only if database is empty or connection fails)
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
                # If document doesn't exist, create it with defaults
                save_config(DEFAULT_URLS)
                return DEFAULT_URLS
    except Exception as e:
        st.warning(f"⚠️ Using default config (Offline/Error): {e}")
        return DEFAULT_URLS
    return DEFAULT_URLS

def save_config(data):
    """Save URLs to Firebase Firestore."""
    try:
        db = get_db()
        if db:
            doc_ref = db.collection("settings").document("unit_config")
            doc_ref.set(data)
    except Exception as e:
        st.error(f"❌ Failed to save to Cloud: {e}")

# Initialize Session State for Admin
if 'admin_logged_in' not in st.session_state:
    st.session_state.admin_logged_in = False
if 'show_login' not in st.session_state:
    st.session_state.show_login = False

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

/* ================= KPI Cards ================= */
.metric-container {
    background: #ffffff;
    padding: 16px;
    border-radius: 14px;
    border: 1px solid #000000;
    box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    margin-bottom: 10px;
}
.metric-label { font-size: 13px; font-weight: 700; text-transform: uppercase; margin-bottom: 4px; color:black; opacity:0.7;}
.metric-value { font-size: 24px; font-weight: 800; color:black; }
.metric-sub { font-size: 13px; font-weight: 600; margin-top: 4px; color:black; opacity:0.8;}

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

/* ================= GRAPH STYLING (White BG + Black Border) ================= */
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

# 1. Load Configuration (FROM FIREBASE)
UNIT_URLS = load_config()

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
                month_options = sorted([str(m) for m in df['MONTH_STR'].unique() if str(m) != 'nan' and m != "N/A"])
                if now_dt.day <= 10:
                    target_date = now_dt.replace(day=1) - timedelta(days=1)
                else:
                    target_date = now_dt
                default_month_val = target_date.strftime('%b-%y').upper()
                m_default = [default_month_val] if default_month_val in month_options else []
                sel_month = st.multiselect("📅 Month", month_options, default=m_default, placeholder="All Months")
            
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
        avg_cancut_p = dff['CAN CUT %'].mean()*100 if not dff.empty else 0
        avg_cut_p = dff['CUT %'].mean()*100 if not dff.empty else 0
        avg_std = dff['STD Cons'].mean() if not dff.empty else 0
        avg_cad = dff['CAD Cons'].mean() if not dff.empty else 0
        avg_ach = dff['ACHIEVED CONS'].mean() if not dff.empty else 0

        perf_cut = (sum_cut/sum_cancut*100) if sum_cancut>0 else 0
        perf_rcvd = (sum_rcvd/sum_req*100) if sum_req>0 else 0
        perf_cons = avg_ach-avg_std

        ex1_count = len(dff[dff['CUT %'] < 1])
        ex2_count = len(dff[dff['CAN CUT %'] < 1])
        ex3_count = len(dff[dff['CUT %'] < dff['CAN CUT %']])
        
        def fmt(v): return str(v) if v>0 else "--"

        # KPI Logic
        def card(title, val_str, sub_text, color, filled=False, border_color=None):
            if filled:
                b_col = border_color if border_color else color
                st.markdown(f"""
                <div class="metric-container filled-card" style="background-color: {color}; border-left: 8px solid {b_col};">
                    <div class="metric-label">{title}</div>
                    <div class="metric-value">{val_str}</div>
                    <div class="metric-sub">{sub_text}</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="metric-container" style="border-left: 6px solid {color};">
                    <div class="metric-label">{title}</div>
                    <div class="metric-value">{val_str}</div>
                    <div class="metric-sub" style="color:{color};">{sub_text}</div>
                </div>
                """, unsafe_allow_html=True)

        c_red_bg, c_red_bd = "#fca5a5", "#e11d48"
        c_yel_bg, c_yel_bd = "#fcd34d", "#b45309"
        c_grn_bg, c_grn_bd = "#6ee7b7", "#047857"

        # Color Logic
        cp_bg, cp_bd = (c_grn_bg, c_grn_bd) if perf_cut >= 100 else (c_red_bg, c_red_bd)
        cc_bg, cc_bd = (c_grn_bg, c_grn_bd) if avg_cancut_p > 100 else ((c_yel_bg, c_yel_bd) if avg_cancut_p == 100 else (c_red_bg, c_red_bd))
        cut_bg, cut_bd = (c_grn_bg, c_grn_bd) if avg_cut_p >= avg_cancut_p else (c_red_bg, c_red_bd)
        rcvd_bg, rcvd_bd = (c_grn_bg, c_grn_bd) if sum_rcvd >= sum_req else (c_red_bg, c_red_bd)
        cad_bg, cad_bd = (c_grn_bg, c_grn_bd) if avg_cad <= avg_std else (c_red_bg, c_red_bd)
        ach_bg, ach_bd = (c_grn_bg, c_grn_bd) if avg_ach <= avg_std else (c_red_bg, c_red_bd)
        stock_bg, stock_bd = (c_grn_bg, c_grn_bd) if sum_stock >= 0 else (c_red_bg, c_red_bd)
        cons_bg, cons_bd = (c_red_bg, c_red_bd) if perf_cons > 0 else (c_grn_bg, c_grn_bd)

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        # GRID
        r1 = st.columns(4)
        with r1[0]: card("Can Cut Performance", f"{perf_cut:,.2f}%", "", cp_bg, filled=True, border_color=cp_bd)
        with r1[1]: card("Order Qty", f"{sum_ord:,.0f}", "", c_grn_bg, filled=True, border_color=c_grn_bd)
        with r1[2]: card("Can Cut Qty", f"{sum_cancut:,.0f} ({avg_cancut_p:.2f}%)", "", cc_bg, filled=True, border_color=cc_bd)
        with r1[3]: card("Cut Qty", f"{sum_cut:,.0f} ({avg_cut_p:.2f}%)", "", cut_bg, filled=True, border_color=cut_bd)

        r2 = st.columns(4)
        with r2[0]: card("Fabric Required", f"{sum_req:,.2f}", "", c_grn_bg, filled=True, border_color=c_grn_bd)
        with r2[1]: card("Fabric Received", f"{sum_rcvd:,.2f} ({perf_rcvd:.2f}%)", "", rcvd_bg, filled=True, border_color=rcvd_bd)
        with r2[2]: card("Fabric Used", f"{sum_used:,.2f}", "", c_grn_bg, filled=True, border_color=c_grn_bd)
        with r2[3]: card("Fabric Leftover", f"{sum_stock:,.2f}", "", stock_bg, filled=True, border_color=stock_bd)

        r3 = st.columns(4)
        with r3[0]: card("STD Cons", f"{avg_std:.3f}", "", c_grn_bg, filled=True, border_color=c_grn_bd)
        with r3[1]: card("CAD Cons", f"{avg_cad:.3f}", "", cad_bg, filled=True, border_color=cad_bd)
        with r3[2]: card("Factory Achieved Cons", f"{avg_ach:.3f}", "", ach_bg, filled=True, border_color=ach_bd)
        sym = "+" if perf_cons > 0 else ""
        with r3[3]: card("Cons Performance", f"{sym}{perf_cons:.3f}", "", cons_bg, filled=True, border_color=cons_bd)

        # Exception & Chart
        c1, c2 = st.columns([1, 2])
        with c1:
            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
            def render_centered_card(bg_class, title, count, btn_key, view_id):
                st.markdown(f"""
                <div class="exception-card-container {bg_class}">
                    <div class="ex-text-group">
                        <div class="ex-lbl">{title}</div>
                        <div class="ex-val">{count}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                st.markdown('<div class="info-btn-css">', unsafe_allow_html=True)
                if st.button("ⓘ", key=btn_key):
                     st.session_state.active_exception_view = view_id
                st.markdown('</div>', unsafe_allow_html=True)
                st.markdown('<div class="spacer-area"></div>', unsafe_allow_html=True)

            render_centered_card("bg-indigo", "CUT% < 100%", fmt(ex1_count), "btn_ex1", "ex1")
            render_centered_card("bg-cyan", "CAN CUT% < 100%", fmt(ex2_count), "btn_ex2", "ex2")
            render_centered_card("bg-green", "CUT% < CAN CUT%", fmt(ex3_count), "btn_ex3", "ex3")

        with c2:
            if 'BUYER' in dff.columns and not dff.empty:
                dfc = dff.groupby('BUYER')[['CAN CUT %', 'CUT %']].mean().reset_index()
                dfc['CAN CUT %'] *= 100
                dfc['CUT %'] *= 100
                dfc = dfc.sort_values(by='CAN CUT %', ascending=False)

                fig = go.Figure()
                
                # --- GRAPH: BARS FIRST, THEN TREND LINE ---
                # 1. Dark Blue Bar (Can Cut)
                fig.add_trace(go.Bar(
                    x=dfc['BUYER'], y=dfc['CAN CUT %'], name="Can Cut %", 
                    marker=dict(color="#2c6e9e", line=dict(width=0)), # Darker Blue match
                    text=[f"{v:.1f}%" for v in dfc['CAN CUT %']], textposition="auto",
                    textfont=dict(color="white", size=13),
                    hovertemplate="<b>%{x}</b><br>Can Cut: %{y:.2f}%<extra></extra>",
                    marker_cornerradius=10
                ))
                
                # 2. Light Blue Bar (Cut)
                fig.add_trace(go.Bar(
                    x=dfc['BUYER'], y=dfc['CUT %'], name="Cut %", 
                    marker=dict(color="#5fa6e1", line=dict(width=0)), # Lighter Blue match
                    text=[f"{v:.1f}%" for v in dfc['CUT %']], textposition="auto",
                    textfont=dict(color="white", size=13),
                    hovertemplate="<b>%{x}</b><br>Cut: %{y:.2f}%<extra></extra>",
                    marker_cornerradius=10
                ))

                # 3. Red Trend Line (On Top)
                fig.add_trace(go.Scatter(
                    x=dfc['BUYER'], y=dfc['CUT %'], mode='lines+markers', name='Cut % Trend',
                    line=dict(color="#e11d48", width=3), # Red
                    marker=dict(size=10, color="#e11d48", line=dict(width=2, color='white')),
                    showlegend=False, hoverinfo='skip'
                ))

                fig.update_layout(
                    title=dict(text="📈 Performance by Buyer (Can Cut vs Cut)", x=0.01, font=dict(size=26, color="#1e293b", family="Arial", weight=700)),
                    hovermode="x unified", barmode='group', 
                    plot_bgcolor='rgba(255, 255, 255, 1)', # White background inside plot
                    paper_bgcolor='rgba(0,0,0,0)', # Transparent paper to show the container border
                    height=400, bargap=0.2,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=0.98),
                    yaxis=dict(showline=False, zeroline=False),
                    xaxis=dict(showgrid=False, showline=True, linecolor="#cbd5e1"),
                    margin=dict(l=40, r=50, t=60, b=70)
                )
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': True, 'displaylogo': False})
            else:
                st.info("No data available for the selected filters.")

        # Detail Table
        if st.session_state.active_exception_view:
            st.markdown("---")
            detail_df = pd.DataFrame()
            view_title = ""
            view_color = ""

            if st.session_state.active_exception_view == 'ex1':
                detail_df = dff[dff['CUT %'] < 1].copy()
                view_title = "🚨 Orders with CUT % < 100%"
                view_color = "#6366f1"
            elif st.session_state.active_exception_view == 'ex2':
                detail_df = dff[dff['CAN CUT %'] < 1].copy()
                view_title = "⚠️ Orders with CAN CUT % < 100%"
                view_color = "#06b6d4"
            elif st.session_state.active_exception_view == 'ex3':
                detail_df = dff[dff['CUT %'] < dff['CAN CUT %']].copy()
                view_title = "📉 Orders where CUT % < CAN CUT %"
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