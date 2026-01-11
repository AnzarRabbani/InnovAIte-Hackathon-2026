from datetime import datetime, timedelta

# =====================================================
# SCIENTIFICALLY GROUNDED CONSTANTS
# =====================================================

# AI inference energy (enterprise data centers)
# ~2.5 µWh per token (OpenAI / Meta / academic avg)
ENERGY_PER_TOKEN_KWH = 2.5e-6  

# Average water usage for data center cooling
# (Google + AWS sustainability reports)
WATER_PER_KWH_LITERS = 0.49  

# Global average enterprise electricity cost
COST_PER_KWH_USD = 0.12  

# App limits
MAX_TOKENS_PER_DAY = 8000
MAX_PROMPTS_PER_DAY = 7


# =====================================================
# DAILY RESET LOGIC
# =====================================================

def reset_daily_limits_if_needed(user):
    now = datetime.utcnow()

    if now - user.last_prompt_reset >= timedelta(days=1):
        user.daily_prompts_used = 0
        user.daily_token_usage = 0
        user.last_prompt_reset = now


# =====================================================
# AI SUSTAINABILITY INDEX (ASI)
# =====================================================

def calculate_asi(tokens_used: int, prompts_used: int):
    """
    Calculates:
    - ASI score (0–100)
    - Real energy saved (kWh)
    - Real water saved (liters)
    - Real cost saved (USD)
    """

    tokens_saved = max(0, MAX_TOKENS_PER_DAY - tokens_used)

    # Real resource savings
    energy_saved_kwh = tokens_saved * ENERGY_PER_TOKEN_KWH
    water_saved_liters = energy_saved_kwh * WATER_PER_KWH_LITERS
    cost_saved_usd = energy_saved_kwh * COST_PER_KWH_USD

    # Normalized usage fractions
    token_fraction = tokens_used / MAX_TOKENS_PER_DAY
    prompt_fraction = prompts_used / MAX_PROMPTS_PER_DAY

    # Weighted ASI score
    asi_score = (
        0.4 * (1 - token_fraction) +   # server load / energy
        0.4 * (1 - token_fraction) +   # water
        0.2 * (1 - prompt_fraction)    # cost
    ) * 100

    return {
        "asi_score": round(asi_score, 2),
        "energy_saved_kwh": round(energy_saved_kwh, 6),
        "water_saved_liters": round(water_saved_liters, 4),
        "cost_saved_usd": round(cost_saved_usd, 4),
    }


# =====================================================
# PRODUCT SUSTAINABILITY INDEX (PSI)
# =====================================================

def calculate_psi(material_score: float, gradcam_score: float):
    """
    PSI = 60% material lifecycle impact
        + 40% visual inference (Grad-CAM)
    """

    psi = (0.6 * material_score) + (0.4 * gradcam_score)
    return round(psi * 100, 2)
