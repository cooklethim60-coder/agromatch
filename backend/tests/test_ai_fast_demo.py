"""Demo AI must never wait 90 seconds or leak credentials in errors."""
import asyncio
import pytest
import ai


@pytest.fixture(autouse=True)
def reset_cache():
    ai._CACHE.clear()
    yield
    ai._CACHE.clear()


@pytest.mark.asyncio
async def test_identical_request_returns_cached_response(monkeypatch):
    monkeypatch.setenv("AI_PRIMARY_PROVIDER", "gemini")
    monkeypatch.setenv("AI_PRIMARY_API_KEY", "fake-test-key")
    monkeypatch.setenv("AI_PRIMARY_MODEL", "test-model")
    calls = []

    async def fake(p, system, msgs):
        calls.append(1)
        return "Prechecked answer"

    monkeypatch.setattr(ai, "_gemini", fake)
    first = await ai.complete("farm 1", [{"role": "user", "content": "question"}])
    second = await ai.complete("farm 1", [{"role": "user", "content": "question"}])
    assert first[0] == second[0] == "Prechecked answer"
    assert len(calls) == 1
    assert second[1].endswith(":cached")


@pytest.mark.asyncio
async def test_cache_never_crosses_farms_or_messages(monkeypatch):
    monkeypatch.setenv("AI_PRIMARY_PROVIDER", "gemini")
    monkeypatch.setenv("AI_PRIMARY_API_KEY", "fake-test-key")
    monkeypatch.delenv("AI_BACKUP_PROVIDER", raising=False)
    calls = []

    async def fake(p, system, msgs):
        calls.append(1)
        return f"answer {len(calls)}"

    monkeypatch.setattr(ai, "_gemini", fake)
    x = [{"role": "user", "content": "question"}]
    assert (await ai.complete("farm A", x))[0] == "answer 1"
    assert (await ai.complete("farm B", x))[0] == "answer 2"
    assert (await ai.complete("farm A", [{"role": "user", "content": "different"}]))[0] == "answer 3"


@pytest.mark.asyncio
async def test_fast_timeout_and_backup(monkeypatch):
    monkeypatch.setenv("AI_PRIMARY_PROVIDER", "gemini")
    monkeypatch.setenv("AI_PRIMARY_API_KEY", "fake-test-key")
    monkeypatch.setenv("AI_BACKUP_PROVIDER", "openai")
    monkeypatch.setenv("AI_BACKUP_API_KEY", "fake-backup-key")
    monkeypatch.setenv("AI_REQUEST_TIMEOUT_SECONDS", "3")

    async def primary(p, system, msgs):
        raise asyncio.TimeoutError()

    async def backup(p, system, msgs):
        return "backup answer"

    monkeypatch.setattr(ai, "_gemini", primary)
    monkeypatch.setattr(ai, "_openai", backup)
    result = await ai.complete("system", [{"role": "user", "content": "hello"}])
    assert result[0] == "backup answer"
    assert result[1].startswith("backup:")


def test_timeout_clamps(monkeypatch):
    monkeypatch.setenv("AI_REQUEST_TIMEOUT_SECONDS", "900")
    assert ai._request_timeout() == 45.0
    monkeypatch.setenv("AI_REQUEST_TIMEOUT_SECONDS", "not a number")
    assert ai._request_timeout() == 9.0
