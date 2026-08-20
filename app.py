from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime
import joblib
import json
import pandas as pd
import gc

from calculations import calculate_baseline_units, apply_calibration
from weather import get_current_weather
from tariff import calculate_bill
from recommendations import generate_recommendations
from explainability import create_explainer, explain_prediction

# ===== App Setup =====
app = Flask(__name__)
app.config['SECRET_KEY'] = 'change-this-later-to-something-random'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ===== Load ML Model (once, at startup) =====
model = joblib.load('model/best_model.pkl')
with open('model/feature_columns.json', 'r') as f:
    feature_columns = json.load(f)
with open('model/y_train_mean.json', 'r') as f:
    y_train_mean = json.load(f)['y_train_mean']

print("DEBUG STARTUP - Model type:", type(model))
print("DEBUG STARTUP - Feature columns:", feature_columns)
print("DEBUG STARTUP - y_train_mean:", y_train_mean)

# ===== Database Models =====
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

class Prediction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    predicted_units = db.Column(db.Float, nullable=False)
    estimated_bill = db.Column(db.Float, nullable=False)
    connection_type = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# ===== Routes =====
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already taken. Please choose another.')
            return redirect(url_for('signup'))

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(username=username, password_hash=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        flash('Account created successfully! Please log in.')
        return redirect(url_for('login'))

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password. Please try again.')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return redirect(url_for('input_form'))

@app.route('/input-form', methods=['GET', 'POST'])
@login_required
def input_form():
    if request.method == 'POST':
        form_data = request.form

        # ===== Step 1: BEE-based baseline =====
        daily_units, breakdown, fixed_daily, weather_sensitive_daily = calculate_baseline_units(form_data)
        print("\n" + "="*60)
        print("DEBUG 1 - Raw baseline daily units:", daily_units)
        print("DEBUG 1 - Breakdown:", breakdown)
        print("DEBUG 1 - Fixed (non-weather) daily:", fixed_daily)
        print("DEBUG 1 - Weather-sensitive daily:", weather_sensitive_daily)

        # ===== Step 2: Calibration =====
        actual_units_input = form_data.get('actual_units')
        calibrated_daily_units, calibration_factor = apply_calibration(daily_units, actual_units_input)
        calibration_ratio = calibrated_daily_units / daily_units if daily_units > 0 else 1.0
        print("DEBUG 2 - Actual units entered:", actual_units_input)
        print("DEBUG 2 - Calibration factor:", calibration_factor)

        calibrated_fixed_monthly = fixed_daily * 30 * calibration_ratio
        calibrated_weather_sensitive_monthly = weather_sensitive_daily * 30 * calibration_ratio
        print("DEBUG 2 - Calibrated fixed monthly:", round(calibrated_fixed_monthly, 2))
        print("DEBUG 2 - Calibrated weather-sensitive monthly:", round(calibrated_weather_sensitive_monthly, 2))

        # ===== Step 3: Live Weather Fetch =====
        city = form_data.get('city', 'Nagpur')
        weather = get_current_weather(city)
        print("DEBUG 3 - City entered:", city)
        print("DEBUG 3 - Weather source:", weather.get('source'))
        print("DEBUG 3 - Full weather data:", weather)

        # ===== Step 4: ML Model Prediction =====
        now = datetime.now()
        city_encoded_value = 0

        model_input = pd.DataFrame([{
            'day': now.day,
            'month': now.month,
            'dayofweek': now.weekday(),
            'T2M': weather['T2M'],
            'T2M_MAX': weather['T2M_MAX'],
            'T2M_MIN': weather['T2M_MIN'],
            'PRECTOTCORR': weather['PRECTOTCORR'],
            'WS2M': weather['WS2M'],
            'city_encoded': city_encoded_value
        }])
        model_input = model_input[feature_columns]

        model_prediction = model.predict(model_input)[0]
        print("DEBUG 4 - Raw model prediction:", model_prediction)
        print("DEBUG 4 - y_train_mean:", y_train_mean)

        # ===== Step 5: SHAP Explainability (Restored, Full Version) =====
        print("DEBUG 5 - Starting SHAP explainer creation...")
        shap_explainer = create_explainer(model)
        print("DEBUG 5 - SHAP explainer created successfully.")
        shap_explanation = explain_prediction(shap_explainer, model_input, feature_columns)
        print("DEBUG 5 - SHAP explanation generated successfully.")
        print("DEBUG 5 - SHAP explanation content:", shap_explanation)
        del shap_explainer
        gc.collect()

        # ===== Step 6: Weather Adjustment =====
        weather_adjustment_factor = model_prediction / y_train_mean
        weather_adjustment_factor = max(0.70, min(1.30, weather_adjustment_factor))
        print("DEBUG 6 - Weather adjustment factor:", round(weather_adjustment_factor, 3))

        final_monthly_units = calibrated_fixed_monthly + (calibrated_weather_sensitive_monthly * weather_adjustment_factor)
        print("DEBUG 7 - FINAL monthly units:", round(final_monthly_units, 2))

        # ===== Step 7: Bill Calculation =====
        connection_type = form_data.get('connection_type', 'single_phase')
        estimated_bill = calculate_bill(final_monthly_units, connection_type)
        print("DEBUG 8 - Connection type:", connection_type)
        print("DEBUG 8 - Estimated bill:", estimated_bill)
        print("="*60 + "\n")

        # ===== Step 8: Recommendations =====
        tips = generate_recommendations(breakdown, connection_type)

        # ===== Step 9: Save Prediction =====
        new_prediction = Prediction(
            user_id=current_user.id,
            predicted_units=round(final_monthly_units, 2),
            estimated_bill=estimated_bill,
            connection_type=connection_type
        )
        db.session.add(new_prediction)
        db.session.commit()

        return render_template('dashboard_result.html',
                                final_units=round(final_monthly_units, 2),
                                estimated_bill=estimated_bill,
                                breakdown=breakdown,
                                tips=tips,
                                shap_explanation=shap_explanation)

    return render_template('input_form.html')

@app.route('/history')
@login_required
def history():
    all_predictions = Prediction.query.filter_by(user_id=current_user.id).order_by(Prediction.created_at.desc()).all()
    return render_template('history.html', predictions=all_predictions)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

# ===== Run App =====
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)