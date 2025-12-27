def generate_advice(weather_data: dict, crop: str, growth_stage: str) -> dict:
    """
    Rule-based irrigation and fertilization advice engine.
    """
    temperature = weather_data["main"]["temp"]
    rainfall = weather_data.get("rain", {}).get("1h", 0)

    irrigation_tip = "No irrigation required"
    fertilizer_tip = "No fertilizer required"

    crop = crop.lower()
    growth_stage = growth_stage.lower()

    if crop == "rice":
        if growth_stage == "seedling":
            irrigation_tip = "Light irrigation recommended"
            fertilizer_tip = "Apply nitrogen-based fertilizer"
        elif growth_stage == "flowering":
            irrigation_tip = "Maintain standing water in the field"
            fertilizer_tip = "Apply potassium-based fertilizer"

    elif crop == "wheat":
        if growth_stage == "vegetative":
            irrigation_tip = "Moderate irrigation recommended"
            fertilizer_tip = "Apply nitrogen fertilizer"

    if rainfall > 10:
        irrigation_tip = "Irrigation not required due to sufficient rainfall"

    if temperature > 35:
        irrigation_tip = "Increase irrigation frequency due to high temperature"

    return {
        "irrigation_tip": irrigation_tip,
        "fertilizer_tip": fertilizer_tip,
    }