from typing import Optional, Annotated
from pydantic import BaseModel, Field
from pydantic.config import ConfigDict

# Reglas de validación
TempRango  = Annotated[int, Field(ge=-40, le=85)]
HumRango   = Annotated[int, Field(ge=0,   le=100)]
MargenMin5 = Annotated[int, Field(ge=5)]

class ConfigIn(BaseModel):
    esp_id: str = Field(..., min_length=1, max_length=64)
    temperatura: Optional[TempRango] = None
    humedad_suelo: Optional[HumRango] = None
    humedad_ambiente: Optional[HumRango] = None
    margen: Optional[MargenMin5] = None


class ConfigOut(BaseModel):
    id: int
    temperatura: int
    humedad_suelo: int
    humedad_ambiente: int
    margen: int

    model_config = ConfigDict(from_attributes=True)
