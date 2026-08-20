from bee_data import (AC_WATTAGE, FAN_WATTAGE, FRIDGE_ANNUAL_KWH,
                       GEYSER_WATTAGE, WASHING_MACHINE_WATTAGE,
                       TV_WATTAGE, LIGHT_WATTAGE, COOLER_WATTAGE,
                       MICROWAVE_WATTAGE, WATER_MOTOR_WATTAGE)

WEATHER_SENSITIVE_APPLIANCES = ['AC', 'Air Cooler', 'Geyser']


def safe_int(value, default=0):
    """Empty string ya None ko safely 0 (ya default) mein convert karta hai."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_float(value, default=0.0):
    """Empty string ya None ko safely 0.0 (ya default) mein convert karta hai."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def calculate_baseline_units(form_data):
    """
    Form se aaya data leка, total DAILY baseline units calculate karta hai.
    Appliances ko fixed (weather se unaffected) aur weather-sensitive
    (AC, Cooler, Geyser) mein split karta hai.
    """
    total_daily_units = 0.0
    breakdown = {}

    # ===== AC =====
    ac_count = safe_int(form_data.get('ac_count', 0))
    ac_total = 0.0
    for i in range(1, ac_count + 1):
        tonnage = form_data.get(f'ac_{i}_tonnage')
        star = form_data.get(f'ac_{i}_star')
        hours = safe_float(form_data.get(f'ac_{i}_hours', 0))
        wattage = AC_WATTAGE.get((tonnage, star), 1200)
        units = (wattage * hours) / 1000
        ac_total += units
    total_daily_units += ac_total
    breakdown['AC'] = round(ac_total, 3)

    # ===== Fan =====
    fan_count = safe_int(form_data.get('fan_count', 0))
    fan_total = 0.0
    for i in range(1, fan_count + 1):
        fan_type = form_data.get(f'fan_{i}_type')
        hours = safe_float(form_data.get(f'fan_{i}_hours', 0))
        wattage = FAN_WATTAGE.get(fan_type, 75)
        units = (wattage * hours) / 1000
        fan_total += units
    total_daily_units += fan_total
    breakdown['Fan'] = round(fan_total, 3)

    # ===== Fridge =====
    fridge_count = safe_int(form_data.get('fridge_count', 0))
    fridge_total = 0.0
    for i in range(1, fridge_count + 1):
        fridge_type = form_data.get(f'fridge_{i}_type')
        annual_kwh = FRIDGE_ANNUAL_KWH.get(fridge_type, 350)
        daily_units = annual_kwh / 365
        fridge_total += daily_units
    total_daily_units += fridge_total
    breakdown['Fridge'] = round(fridge_total, 3)

    # ===== Geyser =====
    geyser_count = safe_int(form_data.get('geyser_count', 0))
    geyser_total = 0.0
    for i in range(1, geyser_count + 1):
        geyser_type = form_data.get(f'geyser_{i}_type')
        minutes = safe_float(form_data.get(f'geyser_{i}_minutes', 0))
        hours = minutes / 60
        wattage = GEYSER_WATTAGE.get(geyser_type, 2000)
        units = (wattage * hours) / 1000
        geyser_total += units
    total_daily_units += geyser_total
    breakdown['Geyser'] = round(geyser_total, 3)

    # ===== Washing Machine =====
    wm_count = safe_int(form_data.get('wm_count', 0))
    wm_total = 0.0
    for i in range(1, wm_count + 1):
        wm_type = form_data.get(f'wm_{i}_type')
        times_per_week = safe_float(form_data.get(f'wm_{i}_times_per_week', 0))
        wattage = WASHING_MACHINE_WATTAGE.get(wm_type, 500)
        weekly_units = (wattage * 1 * times_per_week) / 1000
        daily_units = weekly_units / 7
        wm_total += daily_units
    total_daily_units += wm_total
    breakdown['Washing Machine'] = round(wm_total, 3)

    # ===== TV =====
    tv_count = safe_int(form_data.get('tv_count', 0))
    tv_total = 0.0
    for i in range(1, tv_count + 1):
        tv_size = form_data.get(f'tv_{i}_size')
        hours = safe_float(form_data.get(f'tv_{i}_hours', 0))
        wattage = TV_WATTAGE.get(tv_size, 60)
        units = (wattage * hours) / 1000
        tv_total += units
    total_daily_units += tv_total
    breakdown['TV'] = round(tv_total, 3)

    # ===== Lighting =====
    light_count = safe_int(form_data.get('light_count', 0))
    light_type = form_data.get('light_type', 'led')
    light_hours = safe_float(form_data.get('light_hours', 0))
    light_wattage = LIGHT_WATTAGE.get(light_type, 9)
    light_total = (light_wattage * light_count * light_hours) / 1000
    total_daily_units += light_total
    breakdown['Lighting'] = round(light_total, 3)

    # ===== Air Cooler =====
    cooler_count = safe_int(form_data.get('cooler_count', 0))
    cooler_total = 0.0
    for i in range(1, cooler_count + 1):
        hours = safe_float(form_data.get(f'cooler_{i}_hours', 0))
        units = (COOLER_WATTAGE * hours) / 1000
        cooler_total += units
    total_daily_units += cooler_total
    breakdown['Air Cooler'] = round(cooler_total, 3)

    # ===== Microwave =====
    microwave_count = safe_int(form_data.get('microwave_count', 0))
    microwave_total = 0.0
    for i in range(1, microwave_count + 1):
        minutes = safe_float(form_data.get(f'microwave_{i}_minutes', 0))
        hours = minutes / 60
        units = (MICROWAVE_WATTAGE * hours) / 1000
        microwave_total += units
    total_daily_units += microwave_total
    breakdown['Microwave'] = round(microwave_total, 3)

    # ===== Water Motor =====
    motor_count = safe_int(form_data.get('motor_count', 0))
    motor_total = 0.0
    for i in range(1, motor_count + 1):
        hp = form_data.get(f'motor_{i}_hp')
        minutes = safe_float(form_data.get(f'motor_{i}_minutes', 0))
        hours = minutes / 60
        wattage = WATER_MOTOR_WATTAGE.get(hp, 375)
        units = (wattage * hours) / 1000
        motor_total += units
    total_daily_units += motor_total
    breakdown['Water Motor'] = round(motor_total, 3)

    # ===== Other Appliances =====
    other_units = safe_float(form_data.get('other_appliances_units', 0))
    other_daily = other_units / 30
    total_daily_units += other_daily
    breakdown['Other Appliances'] = round(other_daily, 3)

    # ===== Split into Fixed vs Weather-Sensitive =====
    weather_sensitive_daily = sum(breakdown.get(k, 0) for k in WEATHER_SENSITIVE_APPLIANCES)
    fixed_daily = total_daily_units - weather_sensitive_daily

    return round(total_daily_units, 3), breakdown, round(fixed_daily, 3), round(weather_sensitive_daily, 3)


def apply_calibration(baseline_daily_units, actual_units_input):
    """
    User ke real bill se baseline ko nudge karta hai (capped).
    """
    baseline_monthly = baseline_daily_units * 30
    actual_units = safe_float(actual_units_input, default=0)

    if baseline_monthly <= 0 or actual_units <= 0:
        return round(actual_units / 30, 3) if actual_units > 0 else baseline_daily_units, 1.0

    raw_calibration_factor = actual_units / baseline_monthly
    calibration_factor = max(0.5, min(2.0, raw_calibration_factor))
    calibrated_daily_units = baseline_daily_units * calibration_factor

    return round(calibrated_daily_units, 3), round(calibration_factor, 3)