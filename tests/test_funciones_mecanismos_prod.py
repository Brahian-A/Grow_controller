# tests/test_funciones_mecanismos_prod.py
class ESP32Stub:
    def __init__(self):
        self.calls = {"set_bomba": [], "set_ventilador": [], "set_lamparita": []}
        self._snapshot = {"bomba": False, "ventilador": False, "lamparita": False, "nivel_agua": 0}

    def snapshot(self):
        return dict(self._snapshot)

    def set_bomba(self, v: bool):
        self.calls["set_bomba"].append(bool(v))
        self._snapshot["bomba"] = bool(v)

    def set_ventilador(self, v: bool):
        self.calls["set_ventilador"].append(bool(v))
        self._snapshot["ventilador"] = bool(v)

    def set_lamparita(self, v: bool):
        self.calls["set_lamparita"].append(bool(v))
        self._snapshot["lamparita"] = bool(v)


def test_get_status_sin_esp32(funciones_module, monkeypatch):
    # Sin hardware: devuelve/persiste estado en DB sin sync
    monkeypatch.setattr(funciones_module, "_get_esp32_connection", lambda: None)

    from app.db.session import SessionLocal
    with SessionLocal() as db:
        stat = funciones_module.get_status(db)
        assert isinstance(stat.bomba, bool)
        assert isinstance(stat.ventilador, bool)
        assert isinstance(stat.lamparita, bool)
        assert isinstance(stat.nivel_agua, int)


def test_set_mecanismo_con_esp32_y_restaurar(funciones_module, monkeypatch):
    # Estado previo para restaurar
    from app.db.session import SessionLocal
    with SessionLocal() as db:
        prev = funciones_module.get_status(db)
        prev_vals = dict(
            bomba=prev.bomba,
            lamparita=prev.lamparita,
            ventilador=prev.ventilador,
            nivel_agua=prev.nivel_agua,
        )

    stub = ESP32Stub()
    monkeypatch.setattr(funciones_module, "_get_esp32_connection", lambda: stub)

    try:
        out = funciones_module.set_mecanismo(ventilador=True, bomba=False, nivel_agua=77)
        assert out.ventilador is True
        assert out.bomba is False
        assert out.nivel_agua == 77
        assert stub.calls["set_ventilador"] == [True]
        assert stub.calls["set_bomba"] == [False]
        assert stub.calls["set_lamparita"] == []

        # Para verificar persistencia SIN que el snapshot nos “pise” nivel_agua, 
        # deshabilitamos el “hardware” en la lectura:
        monkeypatch.setattr(funciones_module, "_get_esp32_connection", lambda: None)
        with SessionLocal() as db:
            cur = funciones_module.get_status(db)
            assert cur.ventilador is True
            assert cur.bomba is False
            assert cur.nivel_agua == 77

    finally:
        # Restaurar
        funciones_module.set_mecanismo(**prev_vals)
        monkeypatch.setattr(funciones_module, "_get_esp32_connection", lambda: None)
        with SessionLocal() as db:
            cur2 = funciones_module.get_status(db)
            assert cur2.ventilador == prev_vals["ventilador"]
            assert cur2.bomba == prev_vals["bomba"]
            assert cur2.lamparita == prev_vals["lamparita"]
            assert cur2.nivel_agua == prev_vals["nivel_agua"]
