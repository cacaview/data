"""Chat API integration tests."""


def test_suggestions_returns_list(client, sample_trade_records):
    r = client.get("/api/chat/suggestions")
    assert r.status_code == 200
    data = r.json()
    # Response is {"suggestions": [...]} or a list
    suggestions = data.get("suggestions", data) if isinstance(data, dict) else data
    assert isinstance(suggestions, list)


def test_ask_returns_response(client, sample_trade_records):
    r = client.post("/api/chat/ask", json={"message": "什么是RCEP?"})
    assert r.status_code == 200
    data = r.json()
    assert "reply" in data
