import httpx
from dotenv import load_dotenv

load_dotenv()


def send_chat(feature="qa", message="Explain prompt versioning and observability"):
    url = "http://127.0.0.1:8000/chat"
    payload = {
        "user_id": "student-2A202602717",
        "session_id": "session-test-prompt",
        "feature": feature,
        "message": message,
    }
    r = httpx.post(url, json=payload, timeout=30.0)
    data = r.json()
    cid = data.get("correlation_id")
    print(f"Status: {r.status_code} | correlation_id: {cid} | latency: {data.get('latency_ms')}ms")
    return cid


if __name__ == "__main__":
    send_chat()
