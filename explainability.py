import shap

FRIENDLY_NAMES = {
    'day': 'Day of Month',
    'month': 'Time of Year (Month)',
    'dayofweek': 'Day of Week',
    'T2M': 'Average Temperature',
    'T2M_MAX': 'Maximum Temperature',
    'T2M_MIN': 'Minimum Temperature',
    'PRECTOTCORR': 'Rainfall',
    'WS2M': 'Wind Speed',
    'city_encoded': 'Regional Pattern',
}

def create_explainer(model):
    
    return shap.TreeExplainer(model)


def explain_prediction(explainer, model_input, feature_columns):
    """
    SHAP se explanation nikalta hai, exact unit-numbers ke saath.
    """
    shap_values = explainer.shap_values(model_input)

    feature_impact = list(zip(feature_columns, shap_values[0]))
    feature_impact_sorted = sorted(feature_impact, key=lambda x: abs(x[1]), reverse=True)

    top_features = []
    for feature_name, impact_value in feature_impact_sorted[:3]:
        friendly_name = FRIENDLY_NAMES.get(feature_name, feature_name)
        direction = "increased" if impact_value > 0 else "decreased"
        rounded_impact = round(abs(impact_value), 2)

        sentence = f"{friendly_name} {direction} the predicted consumption by approximately {rounded_impact} units."

        top_features.append({
            'feature': friendly_name,
            'sentence': sentence,
            'direction': direction,
            'impact': rounded_impact
        })

    return top_features