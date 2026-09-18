import pytest
from httpx import AsyncClient, ASGITransport
from main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.anyio
async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.anyio
async def test_create_specialty(client):
    response = await client.post("/specialties/", json={"name": "Cardiology", "description": "Heart specialist"})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Cardiology"


@pytest.mark.anyio
async def test_get_specialties(client):
    response = await client.get("/specialties/")
    assert response.status_code == 200


@pytest.mark.anyio
async def test_create_branch(client):
    response = await client.post("/branches/", json={"name": "Main Clinic", "address": "123 Main St"})
    assert response.status_code == 201
    assert response.json()["name"] == "Main Clinic"


@pytest.mark.anyio
async def test_get_branches(client):
    response = await client.get("/branches/")
    assert response.status_code == 200
