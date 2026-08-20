import streamlit as st
import pandas as pd
import joblib
import json
import sqlite3
import bcrypt
from datetime import datetime

from calculations import calculate_baseline_units, apply_calibration
from weather import get_current_weather
from tariff import calculate_bill
from recommendations import generate_recommendations
from explainability import create_explainer, explain_prediction

st.set_page_config(page_title="SmartEnergy", page_icon="⚡", layout="wide")

st.markdown("""
<style>
    .main .block-container { padding-top: 2rem; max-width: 900px; }
    h1, h3 { color: #0F766E; }
    .stButton button { border-radius: 8px; font-weight: 600; }
    div[data-testid="stMetricValue"] { color: #0F766E; font-size: 2rem; }
    .stAlert { border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

MAHARASHTRA_CITIES = [
    "Mumbai", "Pune", "Nagpur", "Nashik", "Aurangabad", "Solapur",
    "Kolhapur", "Amravati", "Thane", "Navi Mumbai", "Mahabaleshwar",
    "Satara", "Sangli", "Akola", "Latur", "Ahmednagar"
]

@st.cache_resource
def load_model():
    model = joblib.load('model/best_model.pkl')
    with open('model/feature_columns.json', 'r') as f:
        feature_columns = json.load(f)
    with open('model/y_train_mean.json', 'r') as f:
        y_train_mean = json.load(f)['y_train_mean']
    return model, feature_columns, y_train_mean

model, feature_columns, y_train_mean = load_model()

def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password_hash TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS predictions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, predicted_units REAL,
                  estimated_bill REAL, connection_type TEXT, created_at TEXT)''')
    conn.commit()
    conn.close()

init_db()

if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'username' not in st.session_state: st.session_state.username = None
if 'page' not in st.session_state: st.session_state.page = 'login'
if 'result' not in st.session_state: st.session_state.result = None

def signup_user(username, password):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    try:
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        c.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, hashed))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def login_user(username, password):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT password_hash FROM users WHERE username=?", (username,))
    result = c.fetchone()
    conn.close()
    if result and bcrypt.checkpw(password.encode('utf-8'), result[0]):
        return True
    return False

def save_prediction(username, units, bill, conn_type):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("INSERT INTO predictions (username, predicted_units, estimated_bill, connection_type, created_at) VALUES (?, ?, ?, ?, ?)",
              (username, units, bill, conn_type, datetime.now().strftime('%Y-%m-%d %H:%M')))
    conn.commit()
    conn.close()

def get_history(username):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT predicted_units, estimated_bill, connection_type, created_at FROM predictions WHERE username=? ORDER BY id DESC", (username,))
    result = c.fetchall()
    conn.close()
    return result

def show_navbar():
    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
    with col1:
        st.markdown(f"### ⚡ SmartEnergy — Welcome, {st.session_state.username}")
    with col2:
        if st.button("🆕 New Prediction", use_container_width=True):
            st.session_state.page = 'form'
            st.session_state.result = None
            st.rerun()
    with col3:
        if st.button("📜 History", use_container_width=True):
            st.session_state.page = 'history'
            st.rerun()
    with col4:
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.session_state.page = 'login'
            st.session_state.result = None
            st.rerun()
    st.divider()

def show_login():
    st.markdown("# ⚡ SmartEnergy")
    st.markdown("### Predict. Explain. Save.")
    st.divider()
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.subheader("Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login", type="primary", use_container_width=True):
            if login_user(username, password):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.page = 'form'
                st.rerun()
            else:
                st.error("Invalid username or password.")
        st.write("")
        if st.button("Don't have an account? Sign Up", use_container_width=True):
            st.session_state.page = 'signup'
            st.rerun()

def show_signup():
    st.markdown("# ⚡ SmartEnergy")
    st.divider()
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.subheader("Create Your Account")
        username = st.text_input("Choose a Username")
        password = st.text_input("Choose a Password", type="password")
        if st.button("Sign Up", type="primary", use_container_width=True):
            if signup_user(username, password):
                st.success("Account created! Please log in.")
                st.session_state.page = 'login'
                st.rerun()
            else:
                st.error("Username already taken.")
        st.write("")
        if st.button("Already have an account? Login", use_container_width=True):
            st.session_state.page = 'login'
            st.rerun()

def show_form():
    show_navbar()
    st.subheader("Tell Us About Your Home")
    form_data = {}

    with st.container(border=True):
        st.markdown("#### ⚡ Connection Type")
        form_data['connection_type'] = st.radio("Select connection type", ["single_phase", "three_phase"], horizontal=True, label_visibility="collapsed")

    with st.container(border=True):
        st.markdown("#### 📍 Your City & Last Bill")
        c1, c2 = st.columns(2)
        form_data['city'] = c1.selectbox("City", MAHARASHTRA_CITIES)
        form_data['actual_units'] = c2.number_input("Last Month's Bill Units", min_value=1.0, step=0.1)

    with st.container(border=True):
        st.markdown("#### ❄️ Air Conditioner (AC)")
        ac_count = st.selectbox("How many ACs do you have?", [0, 1, 2, 3, 4])
        form_data['ac_count'] = ac_count
        for i in range(1, ac_count + 1):
            st.markdown(f"**AC {i} Details**")
            c1, c2, c3 = st.columns(3)
            form_data[f'ac_{i}_tonnage'] = c1.selectbox("Tonnage", ["1", "1.5", "2"], key=f"act{i}")
            form_data[f'ac_{i}_star'] = c2.selectbox("Star Rating", ["3", "5"], key=f"acs{i}")
            form_data[f'ac_{i}_hours'] = c3.number_input("Hours used/day", 0.0, 24.0, step=0.5, key=f"ach{i}")

    with st.container(border=True):
        st.markdown("#### 🌀 Ceiling Fan")
        fan_count = st.selectbox("How many fans do you have?", [0, 1, 2, 3, 4, 5])
        form_data['fan_count'] = fan_count
        for i in range(1, fan_count + 1):
            st.markdown(f"**Fan {i} Details**")
            c1, c2 = st.columns(2)
            form_data[f'fan_{i}_type'] = c1.selectbox("Fan Type", ["standard", "bldc"], key=f"ft{i}")
            form_data[f'fan_{i}_hours'] = c2.number_input("Hours used/day", 0.0, 24.0, step=0.5, key=f"fh{i}")

    with st.container(border=True):
        st.markdown("#### 🧊 Refrigerator")
        fridge_count = st.selectbox("How many refrigerators do you have?", [0, 1, 2])
        form_data['fridge_count'] = fridge_count
        for i in range(1, fridge_count + 1):
            form_data[f'fridge_{i}_type'] = st.selectbox(f"Refrigerator {i} Type", ["single_door", "double_door"], key=f"frt{i}")

    with st.container(border=True):
        st.markdown("#### 🚿 Geyser / Water Heater")
        geyser_count = st.selectbox("How many geysers do you have?", [0, 1, 2])
        form_data['geyser_count'] = geyser_count
        for i in range(1, geyser_count + 1):
            st.markdown(f"**Geyser {i} Details**")
            c1, c2 = st.columns(2)
            form_data[f'geyser_{i}_type'] = c1.selectbox("Type", ["storage", "instant"], key=f"gt{i}")
            form_data[f'geyser_{i}_minutes'] = c2.number_input("Minutes used/day", 0.0, 180.0, step=5.0, key=f"gm{i}")

    with st.container(border=True):
        st.markdown("#### 🧺 Washing Machine")
        wm_count = st.selectbox("How many washing machines do you have?", [0, 1, 2])
        form_data['wm_count'] = wm_count
        for i in range(1, wm_count + 1):
            st.markdown(f"**Washing Machine {i} Details**")
            c1, c2 = st.columns(2)
            form_data[f'wm_{i}_type'] = c1.selectbox("Type", ["top_load", "front_load"], key=f"wmt{i}")
            form_data[f'wm_{i}_times_per_week'] = c2.number_input("Times used/week", 0.0, 14.0, step=1.0, key=f"wmp{i}")

    with st.container(border=True):
        st.markdown("#### 📺 Television (TV)")
        tv_count = st.selectbox("How many TVs do you have?", [0, 1, 2, 3])
        form_data['tv_count'] = tv_count
        for i in range(1, tv_count + 1):
            st.markdown(f"**TV {i} Details**")
            c1, c2 = st.columns(2)
            form_data[f'tv_{i}_size'] = c1.selectbox("Screen Size", ["small", "large"], key=f"tvs{i}")
            form_data[f'tv_{i}_hours'] = c2.number_input("Hours used/day", 0.0, 24.0, step=0.5, key=f"tvh{i}")

    with st.container(border=True):
        st.markdown("#### 💡 Lighting (LED/CFL Bulbs)")
        c1, c2, c3 = st.columns(3)
        form_data['light_count'] = c1.number_input("Number of bulbs", 0, 50, value=0)
        form_data['light_type'] = c2.selectbox("Bulb Type", ["led", "cfl"])
        form_data['light_hours'] = c3.number_input("Avg hours used/day", 0.0, 24.0, step=0.5)

    with st.container(border=True):
        st.markdown("#### 🌬️ Air Cooler")
        cooler_count = st.selectbox("How many air coolers do you have?", [0, 1, 2, 3])
        form_data['cooler_count'] = cooler_count
        for i in range(1, cooler_count + 1):
            form_data[f'cooler_{i}_hours'] = st.number_input(f"Air Cooler {i} — Hours used/day", 0.0, 24.0, step=0.5, key=f"coh{i}")

    with st.container(border=True):
        st.markdown("#### 🍽️ Microwave / Oven")
        microwave_count = st.selectbox("How many microwaves/ovens do you have?", [0, 1, 2])
        form_data['microwave_count'] = microwave_count
        for i in range(1, microwave_count + 1):
            form_data[f'microwave_{i}_minutes'] = st.number_input(f"Microwave {i} — Minutes used/day", 0.0, 180.0, step=5.0, key=f"mwm{i}")

    with st.container(border=True):
        st.markdown("#### 💧 Water Motor / Pump")
        motor_count = st.selectbox("How many water motors do you have?", [0, 1, 2])
        form_data['motor_count'] = motor_count
        for i in range(1, motor_count + 1):
            st.markdown(f"**Water Motor {i} Details**")
            c1, c2 = st.columns(2)
            form_data[f'motor_{i}_hp'] = c1.selectbox("Horsepower (HP)", ["0.5", "1"], key=f"mhp{i}")
            form_data[f'motor_{i}_minutes'] = c2.number_input("Minutes used/day", 0.0, 180.0, step=5.0, key=f"mmin{i}")

    with st.container(border=True):
        st.markdown("#### ➕ Other Appliances")
        form_data['other_appliances_units'] = st.number_input("Estimated units/month from other appliances (optional)", 0.0, step=0.1)

    st.write("")
    if st.button("🔮 Predict My Consumption", type="primary", use_container_width=True):
        if form_data['actual_units'] <= 0:
            st.error("Please enter your last month's bill units.")
        elif (form_data['ac_count'] == 0 and form_data['fan_count'] == 0 and
              form_data['fridge_count'] == 0 and form_data['geyser_count'] == 0 and
              form_data['wm_count'] == 0 and form_data['tv_count'] == 0 and
              form_data['light_count'] == 0 and form_data['cooler_count'] == 0 and
              form_data['microwave_count'] == 0 and form_data['motor_count'] == 0 and
              form_data['other_appliances_units'] == 0):
            st.error("Please enter at least one appliance to get a prediction.")
        else:
            run_prediction(form_data)

def run_prediction(form_data):
    with st.spinner("Calculating your prediction..."):
        daily_units, breakdown, fixed_daily, weather_sensitive_daily = calculate_baseline_units(form_data)
        print("\n" + "="*60)
        print("DEBUG 1 - Raw baseline daily units:", daily_units)
        print("DEBUG 1 - Breakdown:", breakdown)
        print("DEBUG 1 - Fixed (non-weather) daily:", fixed_daily)
        print("DEBUG 1 - Weather-sensitive daily:", weather_sensitive_daily)

        calibrated_daily_units, calibration_factor = apply_calibration(daily_units, form_data['actual_units'])
        calibration_ratio = calibrated_daily_units / daily_units if daily_units > 0 else 1.0
        print("DEBUG 2 - Actual units entered:", form_data['actual_units'])
        print("DEBUG 2 - Calibration factor:", calibration_factor)

        calibrated_fixed_monthly = fixed_daily * 30 * calibration_ratio
        calibrated_weather_sensitive_monthly = weather_sensitive_daily * 30 * calibration_ratio
        print("DEBUG 2 - Calibrated fixed monthly:", round(calibrated_fixed_monthly, 2))
        print("DEBUG 2 - Calibrated weather-sensitive monthly:", round(calibrated_weather_sensitive_monthly, 2))

        weather = get_current_weather(form_data['city'])
        print("DEBUG 3 - City entered:", form_data['city'])
        print("DEBUG 3 - Weather source:", weather.get('source'))
        print("DEBUG 3 - Full weather data:", weather)

        now = datetime.now()
        model_input = pd.DataFrame([{
            'day': now.day, 'month': now.month, 'dayofweek': now.weekday(),
            'T2M': weather['T2M'], 'T2M_MAX': weather['T2M_MAX'], 'T2M_MIN': weather['T2M_MIN'],
            'PRECTOTCORR': weather['PRECTOTCORR'], 'WS2M': weather['WS2M'], 'city_encoded': 0
        }])
        model_input = model_input[feature_columns]

        model_prediction = model.predict(model_input)[0]
        print("DEBUG 4 - Raw model prediction:", model_prediction)
        print("DEBUG 4 - y_train_mean:", y_train_mean)

        shap_explainer = create_explainer(model)
        shap_explanation = explain_prediction(shap_explainer, model_input, feature_columns)
        print("DEBUG 5 - SHAP explanation content:", shap_explanation)

        weather_adjustment_factor = model_prediction / y_train_mean
        weather_adjustment_factor = max(0.70, min(1.30, weather_adjustment_factor))
        print("DEBUG 6 - Weather adjustment factor:", round(weather_adjustment_factor, 3))

        final_monthly_units = calibrated_fixed_monthly + (calibrated_weather_sensitive_monthly * weather_adjustment_factor)
        print("DEBUG 7 - FINAL monthly units:", round(final_monthly_units, 2))

        estimated_bill = calculate_bill(final_monthly_units, form_data['connection_type'])
        tips = generate_recommendations(breakdown, form_data['connection_type'])
        print("DEBUG 8 - Connection type:", form_data['connection_type'])
        print("DEBUG 8 - Estimated bill:", estimated_bill)
        print("="*60 + "\n")

        save_prediction(st.session_state.username, round(final_monthly_units, 2), estimated_bill, form_data['connection_type'])

        st.session_state.result = {
            'final_units': round(final_monthly_units, 2),
            'estimated_bill': estimated_bill,
            'breakdown': breakdown,
            'tips': tips,
            'shap_explanation': shap_explanation,
            'weather': weather,
            'city': form_data['city']
        }
        st.session_state.page = 'dashboard'
    st.rerun()

def show_dashboard():
    show_navbar()
    result = st.session_state.result
    if result is None:
        st.warning("No prediction yet. Click 'New Prediction' to get started.")
        return

    st.subheader("📊 Your Energy Dashboard")

    with st.container(border=True):
        st.markdown(f"#### 🌤️ Live Weather Used for This Prediction — {result['city']}")
        w = result['weather']
        wc1, wc2, wc3, wc4, wc5 = st.columns(5)
        wc1.metric("Avg Temp", f"{w['T2M']}°C")
        wc2.metric("Max Temp", f"{w['T2M_MAX']}°C")
        wc3.metric("Min Temp", f"{w['T2M_MIN']}°C")
        wc4.metric("Rainfall", f"{w['PRECTOTCORR']} mm")
        wc5.metric("Wind Speed", f"{w['WS2M']} m/s")
        st.caption(f"Data source: {w['source']} — fetched live at prediction time")

    col1, col2 = st.columns(2)
    col1.metric("Predicted Next Month", f"{result['final_units']} units")
    col2.metric("Estimated Bill", f"₹{result['estimated_bill']}")

    st.markdown("#### Appliance-wise Contribution")
    for appliance, units in result['breakdown'].items():
        if units > 0:
            st.write(f"**{appliance}**: {units} units/day")

    st.markdown("#### 💡 Personalized Recommendations")
    for tip in result['tips']:
        st.info(tip)

    st.markdown("#### 🔍 Why This Prediction? (Weather Impact)")
    for item in result['shap_explanation']:
        st.write(f"- {item['sentence']}")

    st.caption("This is an estimated base energy bill calculated using standard tariff slabs. Actual bills may vary due to additional charges such as duty and fuel adjustment costs.")

def show_history():
    show_navbar()
    st.subheader("📜 Your Prediction History")
    history = get_history(st.session_state.username)
    if not history:
        st.write("No predictions yet. Click 'New Prediction' to get started.")
    else:
        for units, bill, conn_type, created_at in history:
            st.write(f"**{created_at}** — {units} units — ₹{bill} ({conn_type})")

if not st.session_state.logged_in:
    if st.session_state.page == 'signup':
        show_signup()
    else:
        show_login()
else:
    if st.session_state.page == 'history':
        show_history()
    elif st.session_state.page == 'dashboard':
        show_dashboard()
    else:
        show_form()