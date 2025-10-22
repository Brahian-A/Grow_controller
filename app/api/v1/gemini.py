from fastapi import APIRouter, HTTPException, status, Body
from app.schemas.gemini import GeminiQueryIn, PlantConditionsOut
from app.servicios.funciones import get_plant_conditions

router = APIRouter(prefix="/gemini", tags=["gemini"])

@router.post("/plant-query", response_model=PlantConditionsOut)
def query_plant_conditions(payload: GeminiQueryIn = Body(...)):
    """
    Recibe el nombre de una planta y devuelve sus condiciones óptimas de
    crecimiento consultando a la API de Gemini.
    """
    try:
        conditions = get_plant_conditions(payload.plant_name)
        return conditions
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except ConnectionError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Ocurrió un error inesperado: {e}")