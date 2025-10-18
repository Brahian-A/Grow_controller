# tests/test_funciones_config_prod.py
def test_config_actualiza_y_restaurar(funciones_module):
    # Guardar config actual
    from app.db.session import SessionLocal
    with SessionLocal() as db:
        original = funciones_module.get_config(db)

        orig_vals = dict(
            humedad_suelo_umbral_alto=original.humedad_suelo_umbral_alto,
            humedad_suelo_umbral_bajo=original.humedad_suelo_umbral_bajo,
            temperatura_umbral_alto=original.temperatura_umbral_alto,
            temperatura_umbral_bajo=original.temperatura_umbral_bajo,
            humedad_umbral_alto=original.humedad_umbral_alto,
            humedad_umbral_bajo=original.humedad_umbral_bajo,
        )

    try:
        # Cambiar un par de valores
        nuevo = funciones_module.set_config(
            temperatura_umbral_bajo=18,
            humedad_umbral_alto=65,
        )
        assert nuevo.temperatura_umbral_bajo == 18
        assert nuevo.humedad_umbral_alto == 65

        # Confirmar lectura
        with SessionLocal() as db:
            verif = funciones_module.get_config(db)
            assert verif.temperatura_umbral_bajo == 18
            assert verif.humedad_umbral_alto == 65

    finally:
        # Restaurar
        funciones_module.set_config(**orig_vals)
        with SessionLocal() as db:
            restored = funciones_module.get_config(db)
            assert restored.temperatura_umbral_bajo == orig_vals["temperatura_umbral_bajo"]
            assert restored.humedad_umbral_alto == orig_vals["humedad_umbral_alto"]
