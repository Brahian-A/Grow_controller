from pydantic import BaseModel
from typing import Optional

class ConfigIn(BaseModel):
    humedad_suelo_umbral_alto: Optional[int] = None
    humedad_suelo_umbral_bajo: Optional[int] = None
    temperatura_umbral_alto: Optional[int] = None
    temperatura_umbral_bajo: Optional[int] = None
    humedad_umbral_alto: Optional[int] = None
    humedad_umbral_bajo: Optional[int] = None


class ConfigOut(BaseModel):
    id: int
    humedad_suelo_umbral_alto: int
    humedad_suelo_umbral_bajo: int
    temperatura_umbral_alto: int
    temperatura_umbral_bajo: int
    humedad_umbral_alto: int
    humedad_umbral_bajo: int
    class Config:
        from_attributes = True


