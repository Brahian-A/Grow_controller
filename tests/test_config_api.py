# tests/test_config_api.py
def test_config_por_defecto(app_client):
    r = app_client.get("/config")
    assert r.status_code == 200
    cfg = r.json()
    # no asumimos valores exactos: solo presencia de claves
    for k in [
        "humedad_suelo_umbral_alto", "humedad_suelo_umbral_bajo",
        "temperatura_umbral_alto", "temperatura_umbral_bajo",
        "humedad_umbral_alto", "humedad_umbral_bajo",
        "id"
    ]:
        assert k in cfg


def test_config_update_parcial(app_client):
    # leer actual
    r0 = app_client.get("/config")
    assert r0.status_code == 200
    orig = r0.json()

    try:
        # actualizar
        r = app_client.put("/config", json={"temperatura_umbral_bajo": 18})
        assert r.status_code == 200
        cfg = r.json()
        assert cfg["temperatura_umbral_bajo"] == 18

        # confirmar
        r2 = app_client.get("/config")
        assert r2.status_code == 200
        assert r2.json()["temperatura_umbral_bajo"] == 18
    finally:
        # restaurar
        payload_restore = {k: orig[k] for k in orig if k != "id"}
        r3 = app_client.put("/config", json=payload_restore)
        assert r3.status_code == 200
