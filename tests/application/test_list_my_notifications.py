from tests.application.fakes import OTHER, OWNER, SMS_OK, World


def crear(w: World, owner=OWNER, title="t"):
    w.clock.advance(seconds=1)
    return w.create.execute(
        owner_id=owner, title=title, content="c", channel="sms", recipient=SMS_OK
    )


def test_lista_vacia():
    w = World()
    r = w.list.execute(OWNER, 1, 20)
    assert (r.data, r.total, r.page, r.limit) == ([], 0, 1, 20)


def test_solo_devuelve_las_propias():
    w = World()
    mine = crear(w)
    crear(w, owner=OTHER)
    r = w.list.execute(OWNER, 1, 20)
    assert [n.id for n in r.data] == [mine.id]
    assert r.total == 1


def test_mas_nuevas_primero():
    w = World()
    ids = [crear(w).id for _ in range(3)]
    r = w.list.execute(OWNER, 1, 20)
    assert [n.id for n in r.data] == list(reversed(ids))


def test_empate_de_created_at_se_desempata_por_id_desc():
    w = World()
    a = w.create.execute(owner_id=OWNER, title="a", content="c", channel="sms", recipient=SMS_OK)
    b = w.create.execute(owner_id=OWNER, title="b", content="c", channel="sms", recipient=SMS_OK)
    assert a.created_at == b.created_at
    r = w.list.execute(OWNER, 1, 20)
    assert [n.id for n in r.data] == [b.id, a.id]


def test_paginacion_y_total():
    w = World()
    ids = [crear(w).id for _ in range(5)]
    newest_first = list(reversed(ids))
    p1 = w.list.execute(OWNER, 1, 2)
    p2 = w.list.execute(OWNER, 2, 2)
    p3 = w.list.execute(OWNER, 3, 2)
    assert [n.id for n in p1.data] == newest_first[0:2]
    assert [n.id for n in p2.data] == newest_first[2:4]
    assert [n.id for n in p3.data] == newest_first[4:5]
    assert p1.total == p2.total == p3.total == 5
    assert (p2.page, p2.limit) == (2, 2)


def test_pagina_fuera_de_rango_devuelve_data_vacia_con_total():
    w = World()
    crear(w)
    r = w.list.execute(OWNER, 5, 10)
    assert r.data == []
    assert r.total == 1
