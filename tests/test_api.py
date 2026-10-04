from fastapi.testclient import TestClient
import app.agent as agent_module
from app.main import app

client = TestClient(app)


def test_health_and_page():
    assert client.get('/health').json()['status'] == 'ok'
    assert '健康知识' in client.get('/').text


def test_knowledge_with_source():
    response = client.post('/api/chat', json={'message': '如何健康饮食？'})
    assert response.status_code == 200
    assert response.json()['route'] == 'knowledge'
    assert response.json()['sources'][0]['url'].startswith('https://www.who.int/')


def test_validation():
    for payload in [{}, {'message': '   '}, {'message': 'a' * 1001}, {'message': 123}]:
        assert client.post('/api/chat', json=payload).status_code == 422


def test_boundaries_take_priority_over_knowledge():
    for message, route in [('胸痛时可以运动吗', 'urgent_hint'), ('糖尿病怎么饮食', 'boundary'), ('吃什么药', 'boundary'), ('天文知识', 'unknown')]:
        result = client.post('/api/chat', json={'message': message}).json()
        assert result['route'] == route
        assert result['sources'] == []


def test_topics_and_missing_resource():
    assert client.get('/api/topics', params={'q': '饮食'}).json() == [{'id': 'diet', 'title': '健康饮食'}]
    assert client.get('/api/topics/activity').status_code == 200
    assert client.get('/api/topics/missing').status_code == 404


def test_deepseek_path_without_real_network(monkeypatch):
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'test-key-not-sent')

    async def fake_deepseek(message: str, context: list[str]) -> str:
        assert message == '如何保持健康饮食？'
        assert context
        return '这是测试替身返回的健康知识。'

    monkeypatch.setattr(agent_module, 'ask_deepseek', fake_deepseek)
    response = client.post('/api/chat', json={'message': '如何保持健康饮食？'})

    assert response.status_code == 200
    assert response.json()['mode'] == 'deepseek_api'
    assert response.json()['answer'] == '这是测试替身返回的健康知识。'
