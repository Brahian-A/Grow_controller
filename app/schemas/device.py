from pydantic import BaseModel, Field, ConfigDict, field_serializer
from typing import Optional
from datetime import datetime

class DeviceIn(BaseModel):
    esp_id: str = Field(..., min_length=1, max_length=64)
    nombre: Optional[str] = Field(None, max_length=50)

class DeviceUpdate(BaseModel):
    nombre: Optional[str] = Field(None, max_length=50)
    activo: Optional[bool] = None

class DeviceOut(BaseModel):
    id: int
    esp_id: str
    nombre: Optional[str]
    activo: bool
    ultimo_contacto: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
