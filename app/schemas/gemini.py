from pydantic import BaseModel, Field

class GeminiQueryIn(BaseModel):
    """Schema para la consulta a Gemini."""
    plant_name: str = Field(..., min_length=2, max_length=100, description="Nombre de la planta a consultar.")

class PlantConditionsOut(BaseModel):
    """Schema para la respuesta con las condiciones óptimas de la planta."""
    temperatura: float
    humedad_tierra: float
    humedad_ambiente: float