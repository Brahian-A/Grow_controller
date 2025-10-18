# tests/test_funciones_lecturas_prod.py
def test_agregar_y_ultima_lectura_sobre_db_real(funciones_module):
    created = funciones_module.agregar_lectura(
        temperatura=31.1, humedad=51.0, humedad_suelo=41.0, nivel_de_agua=81.0
    )
    ul = funciones_module.ultima_lectura()
    assert ul is not None
    # la última debería ser la que acabamos de insertar
    assert ul.id == created.id
    assert (ul.temperatura, ul.humedad, ul.humedad_suelo, ul.nivel_de_agua) == (31.1, 51.0, 41.0, 81.0)

    # limpieza
    from app.db.session import SessionLocal
    with SessionLocal() as db:
        from app.db.models import Lectura
        obj = db.get(Lectura, created.id)
        if obj:
            db.delete(obj)
            db.commit()


def test_ultimas_lecturas_limit_con_inserts_recientes(funciones_module):
    # insertamos 3 lecturas nuevas (serán recientes, pero no dependemos del orden)
    cre = []
    for i in range(3):
        cre.append(
            funciones_module.agregar_lectura(
                temperatura=40.0 + i,
                humedad=60.0 + i,
                humedad_suelo=45.0 + i,
                nivel_de_agua=70.0 + i,
            )
        )

    ult3 = funciones_module.ultimas_lecturas(limit=3)
    assert len(ult3) == 3

    # validamos que NUESTROS ids estén entre las últimas 3 (sin asumir orden)
    ult3_ids = {x.id for x in ult3}
    cre_ids = {x.id for x in cre}
    assert cre_ids.issubset(ult3_ids) or len(cre_ids.intersection(ult3_ids)) == 3

    # y que ultima_lectura() coincida con el último que insertamos
    ul = funciones_module.ultima_lectura()
    assert ul is not None and ul.id == cre[-1].id

    # limpieza
    from app.db.session import SessionLocal
    with SessionLocal() as db:
        from app.db.models import Lectura
        for obj in cre:
            db_obj = db.get(Lectura, obj.id)
            if db_obj:
                db.delete(db_obj)
        db.commit()
