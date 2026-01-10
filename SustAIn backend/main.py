from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from database import SessionLocal, Base, engine
from models import User, ForumPost
from auth import get_password_hash, verify_password, create_access_token
from utils import reset_daily_prompts, can_use_gradcam, mark_gradcam_used, calculate_asi, calculate_psi
from gradcam_model import get_gradcam_score
from datetime import datetime
import shutil

Base.metadata.create_all(bind=engine)
app = FastAPI()

MAX_PROMPTS_PER_DAY = 7
MAX_TOKENS_PER_DAY = 8000
MESSAGE_TOKEN_COST = 1200  # average medium/long prompt tokens

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ----- Auth -----
@app.post("/register")
def register(email:str, password:str, db:Session=Depends(get_db)):
    if db.query(User).filter(User.email==email).first():
        raise HTTPException(400,"Email already registered")
    hashed = get_password_hash(password)
    user = User(email=email,password=hashed)
    db.add(user); db.commit()
    return {"message":"User registered"}

@app.post("/login")
def login(form_data:OAuth2PasswordRequestForm=Depends(), db:Session=Depends(get_db)):
    user = db.query(User).filter(User.email==form_data.username).first()
    if not user or not verify_password(form_data.password,user.password):
        raise HTTPException(400,"Invalid credentials")
    token = create_access_token({"sub":user.email})
    return {"access_token":token, "token_type":"bearer"}

# ----- Chatbot -----
@app.post("/chat")
def chat(user_email:str, message:str, db:Session=Depends(get_db)):
    user = db.query(User).filter(User.email==user_email).first()
    if not user: raise HTTPException(404,"User not found")
    reset_daily_prompts(user)
    if user.daily_prompts_used >= MAX_PROMPTS_PER_DAY:
        raise HTTPException(400,"Daily prompt limit reached (7 prompts/day)")
    if user.daily_token_usage + MESSAGE_TOKEN_COST > MAX_TOKENS_PER_DAY:
        raise HTTPException(400,"Daily token limit reached (8000 tokens/day)")
    user.daily_prompts_used += 1
    user.daily_token_usage += MESSAGE_TOKEN_COST
    db.commit()
    return {"response":f"AI Reply to '{message}'",
            "prompts_used":user.daily_prompts_used,
            "tokens_used":user.daily_token_usage}

# ----- ASI -----
@app.get("/asi")
def calculate_asi(prompts_used, max_prompts, tokens_used, max_tokens):
    prompt_fraction = prompts_used / max_prompts
    token_fraction = tokens_used / max_tokens

    # Energy saved via reduced inference
    energy_saved_kwh = (1 - token_fraction) * ENERGY_PER_1000_TOKENS_KWH * 8
    water_saved_liters = energy_saved_kwh * WATER_PER_KWH_LITERS
    cost_saved_usd = energy_saved_kwh * COST_PER_KWH_USD

    asi = (
        0.5 * (1 - token_fraction) +
        0.3 * (energy_saved_kwh / 0.032) +
        0.1 * (water_saved_liters / 10) +
        0.1 * (cost_saved_usd / 1)
    )

    return {
        "asi_score": round(min(asi, 1) * 100, 2),
        "energy_saved_kwh": round(energy_saved_kwh, 3),
        "water_saved_liters": round(water_saved_liters, 2),
        "cost_saved_usd": round(cost_saved_usd, 2)
    }

# ----- PSI -----
@app.post("/psi")
def psi(user_email:str, material_score:float, file:UploadFile=File(...), db:Session=Depends(get_db)):
    user = db.query(User).filter(User.email==user_email).first()
    if not user: raise HTTPException(404,"User not found")
    if not can_use_gradcam(user):
        raise HTTPException(400,"Grad-CAM already used today")
    image_path = f"temp_{datetime.utcnow().timestamp()}.jpg"
    with open(image_path,"wb") as buffer: shutil.copyfileobj(file.file, buffer)
    gradcam_score = get_gradcam_score(image_path)
    mark_gradcam_used(user)
    db.commit()
    psi_score = calculate_psi(material_score, gradcam_score)
    return {"psi":psi_score,"gradcam_score":gradcam_score}

# ----- Forum -----
@app.post("/forum")
def post_forum(user_email:str, content:str, db:Session=Depends(get_db)):
    user = db.query(User).filter(User.email==user_email).first()
    if not user: raise HTTPException(404,"User not found")
    post = ForumPost(user_id=user.id, content=content)
    db.add(post); db.commit()
    return {"message":"Post added"}

@app.get("/forum")
def get_forum(db:Session=Depends(get_db)):
    posts = db.query(ForumPost).order_by(ForumPost.timestamp.desc()).all()
    return [{"user":p.user.email,"content":p.content,"timestamp":p.timestamp} for p in posts]

# ----- News -----
@app.get("/news")
def news():
    return [
        {"title":"AI reduces server energy","link":"#"},
        {"title":"Firms receive sustainability awards","link":"#"},
        {"title":"Water usage drops in AI workflows","link":"#"}
    ]
