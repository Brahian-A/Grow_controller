from pydantic import BaseModel, Field
from datetime import datetime

class LecturaIn(BaseModel):
    temperatura: float = Field(..., ge=0, le=45)
    humedad: float = Field(..., ge=0, le=100)
    humedad_suelo: float = Field(..., ge=0, le=100)
    nivel_de_agua: float = Field(..., ge=0, le=100)


class LecturaOut(BaseModel):
    id: int
    fecha_hora: datetime
    temperatura: float
    humedad: float
    humedad_suelo: float
    nivel_de_agua: float
    
    
    class Config:
        from_attributes = True
