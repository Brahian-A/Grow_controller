from pydantic import BaseModel
from typing import Optional

class MecanismosIn(BaseModel):
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
