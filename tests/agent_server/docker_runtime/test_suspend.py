"""Tests for idle container suspension in DockerConversationRegistry."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import httpx
import pytest
from pydantic import SecretStr

from openhands.agent_server.config import Config
from openhands.agent_server.docker_runtime.registry import (
    ConversationContainer,
    DockerConversationRegistry,
)


def _registry(tmp_path, monkeypatch) -> DockerConversationRegistry:
    monkeypatch.setenv("OH_PERSISTENCE_DIR", str(tmp_path / "persistence"))
    return DockerConversationRegistry(
        Config(
            conversations_path=tmp_path / "conversations",
            workspace_path=tmp_path / "workspaces",
            secret_key=SecretStr("outer-key"),
            conversation_idle_ttl_seconds=120.0,
        )
    )


def _container(conversation_id: UUID) -> ConversationContainer:
    return ConversationContainer(
        host=f"http://127.0.0.1/{conversation_id}",
        api_key="inner-key",
        container_id=f"container-{conversation_id}",
    )


# ------------------------------------------------------------------
# _is_suspendable tests
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_suspendable_when_terminal_status(tmp_path, monkeypatch):
    """Container is suspendable when inner server reports terminal status."""
    reg = _registry(tmp_path, monkeypatch)
    cid = uuid4()
    cont = _container(cid)

    for status in ("finished", "error", "stuck"):
        mock_response = MagicMock()
        mock_response.status_code = 404  # suspend-check not found → fallback

        mock_fallback_response = MagicMock()
        mock_fallback_response.is_error = False
        mock_fallback_response.json.return_value = {
            "items": [{"execution_status": status}]
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=[mock_response, mock_fallback_response])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await reg._is_suspendable(cont)
        assert result is True, f"Expected suspendable for status={status}"


@pytest.mark.asyncio
async def test_not_suspendable_when_running(tmp_path, monkeypatch):
    """Container is NOT suspendable when conversation is still running."""
    reg = _registry(tmp_path, monkeypatch)
    cid = uuid4()
    cont = _container(cid)

    mock_response = MagicMock()
    mock_response.status_code = 404

    mock_fallback_response = MagicMock()
    mock_fallback_response.is_error = False
    mock_fallback_response.json.return_value = {
        "items": [{"execution_status": "running"}]
    }

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=[mock_response, mock_fallback_response])
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await reg._is_suspendable(cont)
    assert result is False


@pytest.mark.asyncio
async def test_not_suspendable_when_idle(tmp_path, monkeypatch):
    """IDLE is NOT terminal — should not suspend a fresh conversation."""
    reg = _registry(tmp_path, monkeypatch)
    cont = _container(uuid4())

    mock_response = MagicMock()
    mock_response.status_code = 404

    mock_fallback_response = MagicMock()
    mock_fallback_response.is_error = False
    mock_fallback_response.json.return_value = {"items": [{"execution_status": "idle"}]}

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=[mock_response, mock_fallback_response])
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await reg._is_suspendable(cont)
    assert result is False


@pytest.mark.asyncio
async def test_not_suspendable_when_inner_unreachable(tmp_path, monkeypatch):
    """If the inner container is unreachable, don't suspend it."""
    reg = _registry(tmp_path, monkeypatch)
    cont = _container(uuid4())

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await reg._is_suspendable(cont)
    assert result is False


@pytest.mark.asyncio
async def test_not_suspendable_when_paused(tmp_path, monkeypatch):
    """PAUSED is NOT terminal — user may resume. Don't suspend."""
    reg = _registry(tmp_path, monkeypatch)
    cont = _container(uuid4())

    mock_response = MagicMock()
    mock_response.status_code = 404

    mock_fallback_response = MagicMock()
    mock_fallback_response.is_error = False
    mock_fallback_response.json.return_value = {
        "items": [{"execution_status": "paused"}]
    }

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=[mock_response, mock_fallback_response])
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await reg._is_suspendable(cont)
    assert result is False


# ------------------------------------------------------------------
# _suspend_idle_containers tests
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_suspend_stops_terminal_container(tmp_path, monkeypatch):
    """A finished container should be stopped and removed from _containers."""
    reg = _registry(tmp_path, monkeypatch)
    cid = uuid4()
    cont = _container(cid)
    reg._containers[cid] = cont

    # Mock _is_suspendable → True
    reg._is_suspendable = AsyncMock(return_value=True)

    # Mock stop() to just remove from _containers
    stopped_ids = []

    async def mock_stop(conversation_id):
        stopped_ids.append(conversation_id)
        async with reg._lock:
            reg._containers.pop(conversation_id, None)

    reg.stop = mock_stop

    await reg._suspend_idle_containers()

    assert cid in stopped_ids
    assert cid not in reg._containers


@pytest.mark.asyncio
async def test_suspend_skips_active_container(tmp_path, monkeypatch):
    """A running conversation should not be suspended."""
    reg = _registry(tmp_path, monkeypatch)
    cid = uuid4()
    cont = _container(cid)
    reg._containers[cid] = cont

    # Mock _is_suspendable → False (running)
    reg._is_suspendable = AsyncMock(return_value=False)

    stopped_ids = []

    async def mock_stop(conversation_id):
        stopped_ids.append(conversation_id)

    reg.stop = mock_stop

    await reg._suspend_idle_containers()

    assert cid not in stopped_ids
    assert cid in reg._containers


@pytest.mark.asyncio
async def test_suspend_skips_deleting_container(tmp_path, monkeypatch):
    """A container being deleted should not be suspended."""
    reg = _registry(tmp_path, monkeypatch)
    cid = uuid4()
    cont = _container(cid)
    reg._containers[cid] = cont
    reg._deleting.add(cid)

    reg._is_suspendable = AsyncMock(return_value=True)

    stopped_ids = []

    async def mock_stop(conversation_id):
        stopped_ids.append(conversation_id)

    reg.stop = mock_stop

    await reg._suspend_idle_containers()

    assert cid not in stopped_ids
    # _is_suspendable should not even be called for deleting containers
    reg._is_suspendable.assert_not_called()


@pytest.mark.asyncio
async def test_suspend_handles_stop_failure_gracefully(tmp_path, monkeypatch):
    """If stopping one container fails, others should still be processed."""
    reg = _registry(tmp_path, monkeypatch)
    cid1 = uuid4()
    cid2 = uuid4()
    reg._containers[cid1] = _container(cid1)
    reg._containers[cid2] = _container(cid2)

    reg._is_suspendable = AsyncMock(return_value=True)

    stopped_ids = []

    async def mock_stop(conversation_id):
        if conversation_id == cid1:
            raise RuntimeError("Docker daemon error")
        stopped_ids.append(conversation_id)
        async with reg._lock:
            reg._containers.pop(conversation_id, None)

    reg.stop = mock_stop

    # Should not raise, even though stopping cid1 fails
    await reg._suspend_idle_containers()

    assert cid2 in stopped_ids
    assert cid1 in reg._containers  # still there because stop failed


# ------------------------------------------------------------------
# Resume after suspend (integration-like)
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resume_after_suspend_via_get_or_create(tmp_path, monkeypatch):
    """After a container is suspended, get_or_create recreates it."""
    reg = _registry(tmp_path, monkeypatch)
    cid = uuid4()
    original = _container(cid)
    reg._containers[cid] = original

    # Suspend: remove from _containers (simulating stop)
    async with reg._lock:
        reg._containers.pop(cid, None)

    # Now get_or_create should build a new container
    resumed = _container(cid)
    resumed.container_id = "new-container-id"
    reg._build_container = lambda conversation_id: resumed

    result = await reg.get_or_create(cid)
    assert result is resumed
    assert result.container_id == "new-container-id"
    assert reg.get(cid) is resumed


# ------------------------------------------------------------------
# start() and shutdown() lifecycle
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_start_creates_suspend_task_when_ttl_set(tmp_path, monkeypatch):
    """start() should launch the suspend loop when TTL is configured."""
    reg = _registry(tmp_path, monkeypatch)
    monkeypatch.setattr(reg, "cleanup_stale_containers", lambda: None)

    await reg.start()

    assert reg._suspend_task is not None
    assert not reg._suspend_task.done()

    # Cleanup
    reg._suspend_task.cancel()
    try:
        await reg._suspend_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_start_no_suspend_task_when_ttl_none(tmp_path, monkeypatch):
    """start() should NOT launch suspend loop when TTL is None."""
    monkeypatch.setenv("OH_PERSISTENCE_DIR", str(tmp_path / "persistence"))
    reg = DockerConversationRegistry(
        Config(
            conversations_path=tmp_path / "conversations",
            workspace_path=tmp_path / "workspaces",
            secret_key=SecretStr("outer-key"),
            conversation_idle_ttl_seconds=None,
        )
    )
    monkeypatch.setattr(reg, "cleanup_stale_containers", lambda: None)

    await reg.start()

    assert reg._suspend_task is None


@pytest.mark.asyncio
async def test_shutdown_cancels_suspend_task(tmp_path, monkeypatch):
    """shutdown() should cancel the suspend loop task."""
    reg = _registry(tmp_path, monkeypatch)
    monkeypatch.setattr(reg, "cleanup_stale_containers", lambda: None)

    await reg.start()
    assert reg._suspend_task is not None

    await reg.shutdown()
    assert reg._suspend_task is None
