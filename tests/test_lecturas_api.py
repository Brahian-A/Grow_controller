# tests/test_lecturas_api.py
def test_crear_y_traer_ultima_lectura(app_client):
    payload = {
        "temperatura": 22.5,
        "humedad": 55.0,
        "humedad_suelo": 40.0,
        "nivel_de_agua": 80.0
    }
    r = app_client.post("/lecturas", json=payload)
    assert r.status_code == 201
    data = r.json()
    lectura_id = data["id"]

    r2 = app_client.get("/lecturas/ultima")
    assert r2.status_code == 200
    ul = r2.json()
    assert ul is not None and ul["id"] == lectura_id

    # cleanup
    from app.db.session import SessionLocal
    from app.db.models import Lectura
    with SessionLocal() as db:
        obj = db.get(Lectura, lectura_id)
        if obj:
            db.delete(obj)
            db.commit()


def test_limit_1_devuelve_la_ultima(app_client):
    # Creamos una lectura “marcada” que podamos reconocer
    payload = {"temperatura": 33.3, "humedad": 66.6, "humedad_suelo": 44.4, "nivel_de_agua": 77.7}
    r = app_client.post("/lecturas", json=payload)
    assert r.status_code == 201
    created = r.json()

    try:
        r2 = app_client.get("/lecturas?limit=1")
        assert r2.status_code == 200
        arr = r2.json()
        assert len(arr) == 1
        # la única debería coincidir con la última creada por este test
        assert arr[0]["id"] == created["id"]
    finally:
        # cleanup
        from app.db.session import SessionLocal
        from app.db.models import Lectura
        with SessionLocal() as db:
            obj = db.get(Lectura, created["id"])
            if obj:
                db.delete(obj)
                db.commit()


def test_validacion_pydantic(app_client):
    bad = {
        "temperatura": 99,  # >45
        "humedad": 50,
        "humedad_suelo": 30,
        "nivel_de_agua": 70
    }
    r = app_client.post("/lecturas", json=bad)
    assert r.status_code == 422
