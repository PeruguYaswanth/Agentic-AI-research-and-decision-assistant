import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.db.database import init_db

@pytest.mark.asyncio
async def test_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

@pytest.mark.asyncio
async def test_chat_and_history_endpoints():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Chat / Research
        chat_payload = {
            "question": "Should I use FastAPI or Django for building an AI-powered resume screening application?"
        }
        res = await client.post("/api/chat", json=chat_payload)
        assert res.status_code == 200
        data = res.json()
        assert "session_id" in data
        assert "final_answer" in data
        assert len(data["execution_logs"]) > 0
        assert len(data["sources"]) > 0

        # History
        hist_res = await client.get("/api/research/history")
        assert hist_res.status_code == 200
        hist_data = hist_res.json()
        assert len(hist_data) >= 1
