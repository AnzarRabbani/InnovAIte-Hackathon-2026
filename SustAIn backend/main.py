from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import os
import google.generativeai as genai

from database import SessionLocal, engine
from models import UserUsage, Base
from utils import calculate_asi
from gradcam_model import get_gradcam_score

# ---------- Setup ----------
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY missing")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-pro")

Base.metadata.create_all(bind=engine)

app = FastAPI()

# ---------- Limits ----------
MAX_PROMPTS_PER_DAY = 7
MAX_TOKENS_PER_DAY = 8000
MAX_GRADCAM_PER_DAY = 1

# ---------- DB Dependency ----------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------- Schemas ----------
class ChatRequest(BaseModel):
    user_id: str
    message: str

# ---------- Routes ----------
@app.post("/chat")
def chat(req: ChatRequest, db: Session = Depends(get_db)):
    user = db.query(UserUsage).filter(UserUsage.user_id == req.user_id).first()

    if not user:
        user = UserUsage(user_id=req.user_id)
        db.add(user)
        db.commit()
        db.refresh(user)

    if user.prompts_used >= MAX_PROMPTS_PER_DAY:
        raise HTTPException(429, "Daily prompt limit reached")

    response = model.generate_content(req.message)
    reply = response.text
    tokens_used = response.usage_metadata.total_token_count

    if user.tokens_used + tokens_used > MAX_TOKENS_PER_DAY:
        raise HTTPException(429, "Daily token limit exceeded")

    user.prompts_used += 1
    user.tokens_used += tokens_used
    db.commit()

    asi, energy_saved, water_saved = calculate_asi(
        user.tokens_used, MAX_TOKENS_PER_DAY
    )

    return {
        "reply": reply,
        "tokens_used": tokens_used,
        "prompts_left": MAX_PROMPTS_PER_DAY - user.prompts_used,
        "tokens_left": MAX_TOKENS_PER_DAY - user.tokens_used,
        "ASI": asi,
        "energy_saved_kWh": energy_saved,
        "water_saved_liters": water_saved
    }

@app.post("/gradcam/{user_id}")
def gradcam(user_id: str, db: Session = Depends(get_db)):
    user = db.query(UserUsage).filter(UserUsage.user_id == user_id).first()

    if not user:
        user = UserUsage(user_id=user_id)
        db.add(user)
        db.commit()
        db.refresh(user)

    if user.gradcam_used >= MAX_GRADCAM_PER_DAY:
        raise HTTPException(429, "Grad-CAM daily limit reached")

    score = get_gradcam_score()
    user.gradcam_used += 1
    db.commit()

    return {
        "PSI": round(score * 100, 2),
        "uses_left": MAX_GRADCAM_PER_DAY - user.gradcam_used
    }
