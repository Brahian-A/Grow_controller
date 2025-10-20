from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class LecturaIn(BaseModel):
    esp_id: str = Field(..., min_length=1, max_length=64)
    temperatura: float = Field(..., ge=-0, le=50)
    humedad: float = Field(..., ge=0, le=100)
    humedad_suelo: float = Field(..., ge=0, le=100)
    nivel_de_agua: float = Field(..., ge=0, le=100)


class LecturaOut(BaseModel):
    id: int
    device_id: int
    fecha_hora: datetime
    temperatura: float
    humedad: float
    humedad_suelo: float
    nivel_de_agua: float
    esp_id: Optional[str] = None


    class Config:
        from_attributes = True
