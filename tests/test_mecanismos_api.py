# tests/test_mecanismos_api.py
def test_mecanismos_por_defecto(app_client):
    r = app_client.get("/mecanismos")
    assert r.status_code == 200
    data = r.json()
    for k in ["id", "bomba", "lamparita", "ventilador", "nivel_agua", "alerta_agua"]:
        assert k in data


def test_cambiar_ventilador_y_restaurar(app_client):
    # leer actual
    r0 = app_client.get("/mecanismos")
    assert r0.status_code == 200
    orig = r0.json()

    try:
        r = app_client.put("/mecanismos", json={"ventilador": True})
        assert r.status_code == 200
        assert r.json()["ventilador"] is True

        r2 = app_client.get("/mecanismos")
        assert r2.status_code == 200
        assert r2.json()["ventilador"] is True
    finally:
        # restaurar
        r3 = app_client.put("/mecanismos", json={"ventilador": orig["ventilador"]})
        assert r3.status_code == 200
