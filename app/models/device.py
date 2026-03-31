from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from app.db.database import Base


class Device(Base):
    __tablename__ = "devices"

    id_device = Column(Integer, primary_key=True, index=True)
    id_room = Column(Integer, ForeignKey("rooms.id_room"))

    name = Column(String)
    shelly_id = Column(String)

    device_type = Column(String)
    energy_class = Column(String)

    is_active = Column(Boolean)