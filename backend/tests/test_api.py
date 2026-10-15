"""API integration tests (CLAUDE.md 12.4, 12.12).

Covers auth, the check endpoint, trusted/family CRUD, the family alert, and
authorization isolation (one user cannot touch another's rows → 404).
"""

from __future__ import annotations

from tests.conftest import auth, register


async def test_health_is_minimal(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_check_requires_auth(client):
    resp = await client.post("/api/check", json={"message": "hola"})
    assert resp.status_code == 401


async def test_register_and_check_flow(client):
    token = await register(client, "allan@example.com")
    resp = await client.post(
        "/api/check",
        headers=auth(token),
        json={"message": "Comparta su codigo OTP para desbloquear su cuenta", "language": "es"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["risk_level"] == "high"
    assert body["partial"] is False
    assert any(e["type"] == "otp_request" for e in body["evidence"])


async def test_duplicate_registration_is_generic(client):
    await register(client, "dup@example.com")
    resp = await client.post(
        "/api/auth/register",
        json={"email": "dup@example.com", "password": "Sup3rSecret!"},
    )
    # Same generic 401 as a bad login — no email enumeration.
    assert resp.status_code == 401


async def test_login_wrong_password_is_generic(client):
    await register(client, "login@example.com", password="RightPass123")
    resp = await client.post(
        "/api/auth/login",
        json={"email": "login@example.com", "password": "WrongPass123"},
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid email or password."


async def test_trusted_crud(client):
    token = await register(client, "crud@example.com")
    # Create.
    resp = await client.post(
        "/api/trusted",
        headers=auth(token),
        json={
            "kind": "bank",
            "name": "BAC",
            "domains": ["baccredomatic.com"],
            "phones": ["2295-9898"],
            "emails": [],
        },
    )
    assert resp.status_code == 201, resp.text
    entity_id = resp.json()["id"]
    # List.
    resp = await client.get("/api/trusted", headers=auth(token))
    assert len(resp.json()) == 1
    # Update.
    resp = await client.put(
        f"/api/trusted/{entity_id}",
        headers=auth(token),
        json={
            "kind": "bank",
            "name": "BAC Credomatic",
            "domains": ["baccredomatic.com"],
            "phones": [],
            "emails": [],
        },
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "BAC Credomatic"
    # Delete.
    resp = await client.delete(f"/api/trusted/{entity_id}", headers=auth(token))
    assert resp.status_code == 204


async def test_invalid_domain_is_rejected(client):
    token = await register(client, "baddomain@example.com")
    resp = await client.post(
        "/api/trusted",
        headers=auth(token),
        json={"kind": "bank", "name": "X", "domains": ["not a domain"], "phones": [], "emails": []},
    )
    assert resp.status_code == 422


async def test_idor_user_cannot_touch_another_users_entity(client):
    token_a = await register(client, "a@example.com")
    token_b = await register(client, "b@example.com")
    resp = await client.post(
        "/api/trusted",
        headers=auth(token_a),
        json={
            "kind": "bank",
            "name": "A-bank",
            "domains": ["a-bank.com"],
            "phones": [],
            "emails": [],
        },
    )
    entity_id = resp.json()["id"]

    # B cannot update or delete A's entity — 404, not 403 (no existence leak).
    resp = await client.put(
        f"/api/trusted/{entity_id}",
        headers=auth(token_b),
        json={
            "kind": "bank",
            "name": "hijacked",
            "domains": ["a-bank.com"],
            "phones": [],
            "emails": [],
        },
    )
    assert resp.status_code == 404
    resp = await client.delete(f"/api/trusted/{entity_id}", headers=auth(token_b))
    assert resp.status_code == 404
    # A still has it intact.
    resp = await client.get("/api/trusted", headers=auth(token_a))
    assert resp.json()[0]["name"] == "A-bank"


async def test_family_and_alert_flow(client):
    token = await register(client, "family@example.com")
    resp = await client.post(
        "/api/family",
        headers=auth(token),
        json={"name": "Hija", "email": "hija@example.com", "relationship_label": "hija"},
    )
    assert resp.status_code == 201, resp.text
    contact_id = resp.json()["id"]

    # Send an alert (MOCK_MODE: not actually emailed, reported as sent).
    resp = await client.post(
        "/api/alert",
        headers=auth(token),
        json={
            "family_contact_id": contact_id,
            "risk_level": "high",
            "verification_question": "Can you confirm this is real?",
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["sent_ok"] is True


async def test_alert_to_foreign_contact_is_404(client):
    token_a = await register(client, "fa@example.com")
    token_b = await register(client, "fb@example.com")
    resp = await client.post(
        "/api/family",
        headers=auth(token_a),
        json={"name": "A-hija", "email": "ahija@example.com", "relationship_label": "hija"},
    )
    contact_id = resp.json()["id"]
    # B tries to alert A's contact.
    resp = await client.post(
        "/api/alert",
        headers=auth(token_b),
        json={"family_contact_id": contact_id, "risk_level": "high"},
    )
    assert resp.status_code == 404


async def test_message_too_long_is_rejected(client):
    token = await register(client, "long@example.com")
    resp = await client.post(
        "/api/check",
        headers=auth(token),
        json={"message": "a" * 5001},
    )
    assert resp.status_code == 422
