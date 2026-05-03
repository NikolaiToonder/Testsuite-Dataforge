import asyncio
import pytest
from fastapi import FastAPI
import uvicorn
from multiprocessing import Process
import time
import requests

from app.internal.config import Config
from app.internal.notifications import DevxClient, Topics


app = FastAPI()

received_messages = []

@app.post("/workspace/internal/publish/{topic}")
async def receive_publish(topic: str, payload: dict):
    received_messages.append({"topic": topic, "payload": payload})
    return {"status": "ok"}

@app.get("/ready")
async def ready():
    return {"status": "ready"}

@app.get("/messages")
async def get_messages():
    return received_messages

@app.delete("/messages")
async def delete_messages():
    received_messages.clear()
    return {"status": "ok"}

def run_server():
    uvicorn.run(app, host="127.0.0.1", port=8123, log_level="warning")

#This fixture is basically the same as the one databutton provides, just wanted to use it here aswell for isolated testing. 
@pytest.fixture(scope="module")
def devx_server():
    """Runs a real local server simulating the DevX environment to test HTTP boundaries."""
    server_process = Process(target=run_server)
    server_process.start()
    
    server_url = "http://127.0.0.1:8123"
    # Wait for server to come up
    for _ in range(20):
        try:
            res = requests.get(f"{server_url}/ready", timeout=1)
            if res.status_code == 200:
                break
        except Exception:
            time.sleep(0.5)
            
    yield server_url
    
    server_process.terminate()
    server_process.join()

@pytest.fixture(autouse=True)
def setup_teardown(devx_server):
    requests.delete(f"{devx_server}/messages")
    yield
    requests.delete(f"{devx_server}/messages")


#Tests!!

class TestDevxClientIntegration:
    def test_ping_and_wait_for_devx_ready(self, devx_server):
        cfg = Config(DEVX_URL_INTERNAL=devx_server)
        client = DevxClient(cfg)

        is_ready = client.wait_for_devx_ready(max_retries=1, delay=0.1)

        assert is_ready is True
        assert client.ping() is True

    @pytest.mark.asyncio
    async def test_notify_logs_async_sends_correct_http_payload(self, devx_server):
        cfg = Config(DEVX_URL_INTERNAL=devx_server)
        client = DevxClient(cfg)
        await client.notify_logs_async(text="Integration Test Log", level="info")
        
        response = requests.get(f"{devx_server}/messages")
        messages = response.json()

        assert len(messages) == 1
        msg = messages[0]
        assert msg["topic"] == Topics.backend_log.value
        assert msg["payload"]["text"] == "Integration Test Log"
        assert msg["payload"]["level"] == "info"
        assert "timestamp" in msg["payload"]
