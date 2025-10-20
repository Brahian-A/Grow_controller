from pydantic import BaseModel, Field
from typing import Optional

class MecanismosIn(BaseModel):
    esp_id: str = Field(..., min_length=1, max_length=64)
    bomba: Optional[bool] = None
    luz: Optional[bool] = None
    ventilador: Optional[bool] = None

class MecanismosOut(BaseModel):
    id: int
    bomba: bool
    luz: bool
    ventilador: bool

    class Config:
        from_attributes = True
