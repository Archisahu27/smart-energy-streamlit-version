def get_variable_charge(units):
    if units <= 100:
        return 5.56
    elif units <= 300:
        return 12.40
    elif units <= 500:
        return 16.64
    else:
        return 19.13

def calculate_bill(predicted_units, connection_type):
    fixed_charge = 130 if connection_type == "single_phase" else 435
    variable_charge = get_variable_charge(predicted_units)
    base_energy_bill = fixed_charge + (predicted_units * variable_charge)
    return round(base_energy_bill, 2)