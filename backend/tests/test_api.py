"""Tests for API endpoints."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from ..main import app
from ..models import Script, Tag

@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)

@pytest.mark.asyncio
async def test_create_script(client: TestClient, session: AsyncSession):
    """Test creating a script via API."""
    response = client.post(
        "/api/scripts",
        json={
            "name": "test_script",
            "description": "Test script",
            "content": "print('hello')",
            "is_active": True,
            "tags": ["test"],
            "dependencies": [
                {
                    "package_name": "requests",
                    "version_spec": ">=2.25.1"
                }
            ]
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "test_script"
    assert data["description"] == "Test script"
    assert len(data["tags"]) == 1
    assert data["tags"][0]["name"] == "test"
    assert len(data["dependencies"]) == 1
    assert data["dependencies"][0]["package_name"] == "requests"

@pytest.mark.asyncio
async def test_list_scripts(client: TestClient, session: AsyncSession):
    """Test listing scripts via API."""
    # Create a test script
    script = Script(
        name="test_script",
        description="Test script",
        content="print('hello')",
        is_active=True
    )
    session.add(script)
    tag = Tag(name="test")
    script.tags.append(tag)
    await session.commit()

    response = client.get("/api/scripts")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "test_script"
    assert len(data[0]["tags"]) == 1
    assert data[0]["tags"][0]["name"] == "test"

@pytest.mark.asyncio
async def test_update_script(client: TestClient, session: AsyncSession):
    """Test updating a script via API."""
    # Create a test script
    script = Script(
        name="test_script",
        description="Test script",
        content="print('hello')",
        is_active=True
    )
    session.add(script)
    await session.commit()

    response = client.put(
        f"/api/scripts/{script.id}",
        json={
            "name": "updated_script",
            "description": "Updated description",
            "content": "print('updated')",
            "is_active": False,
            "tags": ["new_tag"],
            "dependencies": []
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "updated_script"
    assert data["description"] == "Updated description"
    assert data["content"] == "print('updated')"
    assert not data["is_active"]
    assert len(data["tags"]) == 1
    assert data["tags"][0]["name"] == "new_tag" 