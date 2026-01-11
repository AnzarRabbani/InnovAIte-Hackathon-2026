from sqlalchemy import Column, Integer, String
from database import Base

class UserUsage(Base):
    __tablename__ = "user_usage"

    user_id = Column(String, primary_key=True, index=True)
    prompts_used = Column(Integer, default=0)
    tokens_used = Column(Integer, default=0)
    gradcam_used = Column(Integer, default=0)
