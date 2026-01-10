from sqlalchemy import Column, Integer, String, Float, DateTime
from database import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    daily_prompts_used = Column(Integer, default=0)
    daily_token_usage = Column(Float, default=0.0)
    last_prompt_reset = Column(DateTime, default=datetime.utcnow)
    last_gradcam_used = Column(DateTime, default=None)

class ForumPost(Base):
    __tablename__ = "forum_posts"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    content = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
