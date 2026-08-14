"""End-to-end del happy path contra base real (criterio 15).

Recorre el flujo completo: registro -> login -> crear notificación (que dispara
el envío simulado) -> listar -> consultar -> borrar.
"""


def test_happy_path(client):
    # Registro.
    r = client.post("/auth/register", json={"email": "e2e@ex.com", "password": "secret12345"})
    assert r.status_code == 201
    assert "hashed_password" not in r.json()  # el hash no sale nunca

    # Login.
    r = client.post("/auth/login", json={"email": "e2e@ex.com", "password": "secret12345"})
    assert r.status_code == 200
    token = r.json()["access_token"]
    auth = {"Authorization": f"Bearer {token}"}

    # Crear notificación push (con token de dispositivo): se crea y se "envía".
    r = client.post(
        "/notifications",
        headers=auth,
        json={
            "title": "hola",
            "content": "cuerpo",
            "channel": "push",
            "payload": {"device_token": "dev-abc"},
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "sent"
    assert body["sent_at"] is not None
    notification_id = body["id"]

    # Listar: paginado y con la notificación creada.
    r = client.get("/notifications?page=1&limit=5", headers=auth)
    assert r.status_code == 200
    page = r.json()
    assert page["total"] == 1
    assert page["items"][0]["id"] == notification_id

    # Consultar la propia.
    r = client.get(f"/notifications/{notification_id}", headers=auth)
    assert r.status_code == 200

    # Borrar: 204 sin body.
    r = client.delete(f"/notifications/{notification_id}", headers=auth)
    assert r.status_code == 204
    assert r.content == b""
