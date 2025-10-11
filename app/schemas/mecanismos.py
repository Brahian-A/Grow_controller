from pydantic import BaseModel, Field, model_validator
from typing import Optional


class MecanismosIn(BaseModel):
    bomba: Optional[bool] = None
    lamparita: Optional[bool] = None
    ventilador: Optional[bool] = None
    nivel_agua: Optional[int] = 0


class MecanismosOut(BaseModel):
    id: int
    bomba: bool
    lamparita: bool
    ventilador: bool
    nivel_agua: int
    alerta_agua: bool = False

    class Config:
        from_attributes = True

    @model_validator(mode="after")
    def calcular_alerta_agua(self):
        self.alerta_agua = self.nivel_agua <= 15
        return self
