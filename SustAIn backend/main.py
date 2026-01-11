from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from datetime import datetime

from database import SessionLocal, engine
from models import User
from utils import (
    reset_daily_limits_if_needed,
    calculate_asi,
    calculate_psi,
    MAX_PROMPTS_PER_DAY,
    MAX_TOKENS_PER_DAY
)

from gradcam_model import get_gradcam_score

app = FastAPI()


# =====================================================
# DATABASE DEPENDENCY
# =====================================================

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =====================================================
# CHATBOT ENDPOINT
# =====================================================

@app.post("/chat")
def chat(user_id: int, tokens_used: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    reset_daily_limits_if_needed(user)

    if user.daily_prompts_used >= MAX_PROMPTS_PER_DAY:
        raise HTTPException(status_code=429, detail="Daily prompt limit reached")

    if user.daily_token_usage + tokens_used > MAX_TOKENS_PER_DAY:
        raise HTTPException(status_code=429, detail="Daily token limit reached")

    user.daily_prompts_used += 1
    user.daily_token_usage += tokens_used
    db.commit()

    return {"message": "Chat processed successfully"}


# =====================================================
# ASI ENDPOINT
# =====================================================

@app.get("/asi")
def get_asi(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    reset_daily_limits_if_needed(user)

    return calculate_asi(
        tokens_used=int(user.daily_token_usage),
        prompts_used=user.daily_prompts_used
    )


# =====================================================
# PSI + GRADCAM ENDPOINT
# =====================================================

@app.post("/psi")
def get_psi(
    user_id: int,
    material_score: float,
    image: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Enforce Grad-CAM once per day
    if user.last_gradcam_used and user.last_gradcam_used.date() == datetime.utcnow().date():
        raise HTTPException(status_code=429, detail="Grad-CAM can only be used once per day")

    gradcam_score = get_gradcam_score(image)

    user.last_gradcam_used = datetime.utcnow()
    db.commit()

    psi_score = calculate_psi(material_score, gradcam_score)

    return {
        "psi_score": psi_score,
        "gradcam_score": gradcam_score
    }
