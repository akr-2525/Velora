from sqlalchemy import Column, Integer, String
from backend.db.database import Base

class User(Base):

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String)

    email = Column(String, unique=True)

    interests = Column(String)