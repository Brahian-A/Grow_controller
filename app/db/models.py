from datetime import datetime
from sqlalchemy import Column, Integer, Float, DateTime, Boolean, String, func, Index
from app.db.base import Base

class Lectura(Base):
    __tablename__ = "lecturas"

    id = Column(Integer, primary_key=True, index=True)
    
    fecha_hora = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    temperatura = Column(Float, nullable=False)
    humedad = Column(Float, nullable=False)
    humedad_suelo = Column(Float, nullable=False)
    nivel_de_agua = Column(Float, nullable=False)

# Índices para consultas recientes
Index("index_lecturas_fecha", Lectura.fecha_hora.desc())


class Mecanismos(Base):
    __tablename__ = "mecanismos"

    id = Column(Integer, primary_key=True, index=True)
    
    bomba = Column(Boolean, nullable=False, default=False)
    lamparita = Column(Boolean, nullable=False, default=False)
    ventilador = Column(Boolean, nullable=False, default=False)


class Config(Base):
    __tablename__ = "config"

    id = Column(Integer, primary_key=True, index=True)
    
    humedad_suelo_umbral_alto = Column(Integer, nullable=False, default=55)
    humedad_suelo_umbral_bajo = Column(Integer, nullable=False, default=30)
    temperatura_umbral_alto   = Column(Integer, nullable=False, default=35)
    temperatura_umbral_bajo   = Column(Integer, nullable=False, default=20)
    humedad_umbral_alto       = Column(Integer, nullable=False, default=70)
    humedad_umbral_bajo       = Column(Integer, nullable=False, default=30)


class Evento(Base):
    __tablename__ = "eventos"

    id = Column(Integer, primary_key=True, index=True)
    
    fecha_hora = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    tipo = Column(String(20), nullable=False)
    subtipo = Column(String(50), nullable=False)
