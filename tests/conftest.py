# tests/conftest.py
import os
import importlib
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# 1) Desactivar hardware real en TODOS los tests
@pytest.fixture(scope="session", autouse=True)
def disable_esp32_for_all_tests():
    os.environ["ESP32_ENABLED"] = "false"
    yield

# 2) Asegurar que el esquema exista en la DB REAL antes de cualquier test (no borra nada)
@pytest.fixture(scope="session", autouse=True)
def ensure_schema():
    from app.db.session import engine
    from app.db.base import Base
    import app.db.models  # registra tablas
    Base.metadata.create_all(bind=engine)
    yield

# 3) Módulo funciones reimportado si cambia env
@pytest.fixture
def funciones_module():
    import app.servicios.funciones as funciones
    importlib.reload(funciones)
    return funciones

# 4) TestClient de API SIN montar StaticFiles (evita depender del directorio frontend)
@pytest.fixture
def app_client():
    app = FastAPI(title="Greenhouse API (tests)")

    # Rutas API (mismo enrutado que tu app real)
    from app.api.v1.lecturas import router as lecturas_router
    from app.api.v1.config import router as config_router
    from app.api.v1.mecanismos import router as mecanismos_router
    app.include_router(lecturas_router)
    app.include_router(config_router)
    app.include_router(mecanismos_router)

    return TestClient(app)
