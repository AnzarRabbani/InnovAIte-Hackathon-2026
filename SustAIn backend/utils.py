from datetime import datetime

def reset_daily_prompts(user):
    if user.last_prompt_reset.date() < datetime.utcnow().date():
        user.daily_prompts_used = 0
        user.daily_token_usage = 0
        user.last_prompt_reset = datetime.utcnow()

def can_use_gradcam(user):
    if user.last_gradcam_used is None:
        return True
    return user.last_gradcam_used.date() < datetime.utcnow().date()

def mark_gradcam_used(user):
    user.last_gradcam_used = datetime.utcnow()

def calculate_asi(prompts_used, max_prompts, tokens_used, max_tokens,
                  server_energy_saved, water_saved, cost_saved):
    prompt_fraction = prompts_used / max_prompts
    token_fraction = tokens_used / max_tokens
    w1, w2, w3, w4 = 0.25, 0.25, 0.25, 0.25
    # Combine prompts & tokens into 50% weight, others equally
    asi = 0.5*(1 - 0.5*(prompt_fraction + token_fraction)) + 0.3*server_energy_saved + 0.1*water_saved + 0.1*cost_saved
    return round(asi*100,2)

def calculate_psi(material_score, gradcam_score):
    psi = 0.6*material_score + 0.4*gradcam_score
    return round(psi*100,2)
