"""Chat API integration tests."""


def test_suggestions_returns_list(client, sample_trade_records):
    r = client.get("/api/chat/suggestions")
    assert r.status_code == 200
    data = r.json()
    suggestions = data.get("suggestions", data) if isinstance(data, dict) else data
    assert isinstance(suggestions, list)


def test_ask_returns_response(client, sample_trade_records):
    r = client.post("/api/chat/ask", json={"message": "什么是RCEP?"})
    assert r.status_code == 200
    data = r.json()
    assert "reply" in data


def test_chat_total_trade(client, sample_trade_records):
    response = client.post("/api/chat/ask", json={"message": "中国与东盟贸易总额是多少？"})
    assert response.status_code == 200
    assert "reply" in response.json()


def test_chat_top_partner(client, sample_trade_records):
    response = client.post("/api/chat/ask", json={"message": "哪个国家是中国最大的贸易伙伴？"})
    assert response.status_code == 200
    assert "reply" in response.json()


def test_chat_unknown_question(client, sample_trade_records):
    response = client.post("/api/chat/ask", json={"message": "今天天气怎么样？"})
    assert response.status_code == 200
    assert "reply" in response.json()


def test_chat_rcep(client, sample_trade_records):
    response = client.post("/api/chat/ask", json={"message": "RCEP协定对关税有什么影响？"})
    assert response.status_code == 200
    assert "reply" in response.json()


def test_chat_tariff(client, sample_trade_records):
    response = client.post("/api/chat/ask", json={"message": "电子产品出口到越南的关税是多少？"})
    assert response.status_code == 200
    assert "reply" in response.json()


def test_chat_export(client, sample_trade_records):
    response = client.post("/api/chat/ask", json={"message": "中国对东盟出口的主要产品有哪些？"})
    assert response.status_code == 200
    assert "reply" in response.json()


def test_chat_trend(client, sample_trade_records):
    response = client.post("/api/chat/ask", json={"message": "今年贸易趋势如何？"})
    assert response.status_code == 200
    assert "reply" in response.json()


def test_chat_empty_message(client, sample_trade_records):
    response = client.post("/api/chat/ask", json={"message": ""})
    assert response.status_code == 200
    assert "reply" in response.json()


def test_chat_top_product(client, sample_trade_records):
    response = client.post(
        "/api/chat/ask", json={"message": "2024年贸易增长最快的商品类别是什么？"}
    )
    assert response.status_code == 200
    assert "reply" in response.json()
