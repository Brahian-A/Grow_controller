from datetime import datetime
from sqlalchemy import (
    Column, Integer, Float, DateTime, Boolean, String, func, text,
    ForeignKey, CheckConstraint, Index, UniqueConstraint)
from sqlalchemy.orm import validates, relationship
from app.db.base import Base



class Device(Base):
    __tablename__ = "device"

    id              = Column(Integer, primary_key=True, index=True)
    esp_id          = Column(String(64), unique=True, nullable=False)  # Identificador unico real de la ESP o micro usado 
    nombre          = Column(String(50), nullable=True)
    activo          = Column(Boolean, nullable=False, default=True, server_default=text("1"))
    ultimo_contacto = Column(DateTime(timezone=True), nullable=True)

    # Relaciones
    lecturas   = relationship("Lectura", back_populates="Device", cascade="all, delete-orphan")
    mecanismos = relationship("Mecanismos", back_populates="Device", uselist=False, cascade="all, delete-orphan")
    config     = relationship("Config", back_populates="Device", uselist=False, cascade="all, delete-orphan")
    eventos    = relationship("Evento", back_populates="Device", cascade="all, delete-orphan")



class Lectura(Base):
    __tablename__ = "lecturas"

    id             = Column(Integer, primary_key=True, index=True)
    device_id      = Column(Integer, ForeignKey("device.id", ondelete="CASCADE"), nullable=False, index=True)
    fecha_hora     = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    temperatura    = Column(Float, nullable=False)
    humedad        = Column(Float, nullable=False)
    humedad_suelo  = Column(Float, nullable=False)
    nivel_de_agua  = Column(Float, nullable=False)

    dispositivo = relationship("Device", back_populates="lecturas")

Index("idx_lecturas_device_time", Lectura.device_id, Lectura.fecha_hora)



class Mecanismos(Base):
    __tablename__ = "mecanismos"

    id          = Column(Integer, primary_key=True, index=True)
    device_id   = Column(Integer, ForeignKey("device.id", ondelete="CASCADE"), nullable=False, unique=True)
    bomba       = Column(Boolean, nullable=False, default=False, server_default=text("0"))
    luz         = Column(Boolean, nullable=False, default=False, server_default=text("0"))
    ventilador  = Column(Boolean, nullable=False, default=False, server_default=text("0"))

    dispositivo = relationship("device", back_populates="mecanismos")

    __table_args__ = (
        UniqueConstraint("device_id", name="uq_mecanismos_device"),
    )


class Config(Base):
    __tablename__ = "config"

    id               = Column(Integer, primary_key=True, index=True)
    device_id        = Column(Integer, ForeignKey("device.id", ondelete="CASCADE"), nullable=False, unique=True)

    temperatura      = Column(Integer, nullable=False, default=35)
    humedad_suelo    = Column(Integer, nullable=False, default=55)
    humedad_ambiente = Column(Integer, nullable=False, default=30)
    margen           = Column(Integer, nullable=False, default=5)

    dispositivo = relationship("Device", back_populates="config")

    __table_args__ = (
        CheckConstraint('margen >= 5', name='check_margen_minimo_5'),
        UniqueConstraint('device_id', name='uq_config_device'),
    )

    @validates("margen")
    def _valida_margen(self, key, value):
        if value is None or value < 5:
            raise ValueError("margen debe ser ≥ 5")
        return value


class Evento(Base):
    __tablename__ = "eventos"

    id          = Column(Integer, primary_key=True, index=True)
    device_id   = Column(Integer, ForeignKey("device.id", ondelete="CASCADE"), nullable=False, index=True)
    fecha_hora  = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    tipo        = Column(String(20), nullable=False)
    subtipo     = Column(String(50), nullable=False)
    detalle     = Column(String(255), nullable=False)
    mensaje     = Column(String(255), nullable=False)

    dispositivo = relationship("Device", back_populates="eventos")

Index("idx_eventos_device_time", Evento.device_id, Evento.fecha_hora)
