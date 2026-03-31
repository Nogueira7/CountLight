from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey
from app.db.database import Base


class EnergyReading(Base):
    __tablename__ = "energy_readings"

    id_energy_reading = Column(Integer, primary_key=True, index=True)
    id_device = Column(Integer, ForeignKey("devices.id_device"))

    power_w = Column(Float)
    energy_kwh = Column(Float)
    voltage_v = Column(Float)
    current_a = Column(Float)

    recorded_at = Column(DateTime)