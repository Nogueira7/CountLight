from sqlalchemy import Column, Integer, Float, ForeignKey
from app.db.database import Base


class House(Base):
    __tablename__ = "houses"

    id_house = Column(Integer, primary_key=True, index=True)
    id_user = Column(Integer, ForeignKey("users.id_user"))

    price_per_kwh = Column(Float)