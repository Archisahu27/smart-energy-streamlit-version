REDUCTION_RATES = {
    'AC': 0.12,
    'Geyser': 0.15,
    'Fridge': 0.05,
    'Fan': 0.50,
    'Washing Machine': 0.10,
    'TV': 0.08,
    'Lighting': 0.60,
    'Air Cooler': 0.05,
    'Microwave': 0.03,
    'Water Motor': 0.05,
    'Other Appliances': 0.05,
}

TIPS_MAP = {
    'AC': "Setting the thermostat to 24-26°C instead of lower temperatures",
    'Geyser': "Reducing usage time by a few minutes, or installing a timer",
    'Fridge': "Ensuring the door seals properly and keeping it away from walls for better ventilation",
    'Fan': "Switching to BLDC/5-star rated fans",
    'Washing Machine': "Running full loads instead of multiple small loads",
    'TV': "Fully switching off the TV instead of leaving it on standby",
    'Lighting': "Switching any remaining CFL bulbs to LED",
    'Air Cooler': "Ensuring regular cleaning of cooling pads",
    'Microwave': "Monitoring usage — typically low-impact, no major changes needed",
    'Water Motor': "Using a water-level indicator or timer to avoid overrunning",
    'Other Appliances': "Tracking these appliances individually for more precise recommendations",
}


def generate_recommendations(breakdown, connection_type):
    """
    Appliance-wise breakdown dekh kar, PERSONALIZED recommendations deta hai -
    estimated unit savings aur cost savings ke saath.
    """
    recommendations = []

    total = sum(breakdown.values())
    if total == 0:
        return ["No appliance usage data available to generate recommendations."]

    contributions = {k: (v / total) * 100 for k, v in breakdown.items() if v > 0}
    sorted_contributions = sorted(contributions.items(), key=lambda x: x[1], reverse=True)

    for appliance, percentage in sorted_contributions[:3]:
        daily_units = breakdown.get(appliance, 0)
        monthly_units = daily_units * 30

        reduction_rate = REDUCTION_RATES.get(appliance, 0.05)
        estimated_savings_units = round(monthly_units * reduction_rate, 1)

        approx_rate = 12.40
        estimated_savings_cost = round(estimated_savings_units * approx_rate, 0)

        tip = TIPS_MAP.get(appliance, "Consider monitoring this appliance's usage.")

        recommendations.append(
            f"{appliance} contributes {percentage:.1f}% of your predicted consumption "
            f"({round(monthly_units, 1)} units/month). {tip} could save approximately "
            f"{estimated_savings_units} units/month (~₹{int(estimated_savings_cost)})."
        )

    if total * 30 > 500:
        recommendations.append(
            "Your usage falls in the highest tariff slab (500+ units). Reducing consumption "
            "by even a small amount could move you to a lower slab, saving disproportionately "
            "more due to non-linear tariff pricing."
        )

    return recommendations