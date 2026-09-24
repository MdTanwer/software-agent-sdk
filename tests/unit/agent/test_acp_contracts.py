"""Unit tests for ACP typed contracts."""

import pytest
from pydantic import ValidationError

from openhands.sdk.agent.acp_contracts import (
    AcpSessionState,
    AuthMethod,
    BackgroundTaskSlot,
    McpCapabilities,
    ModelInfo,
    RequestError,
    SessionConfigOption,
    TraceNode,
    VersionedCredentialBinding,
)


class TestSessionConfigOption:
    """Tests for SessionConfigOption contract."""

    def test_valid_session_config_option(self):
        """Test creating valid session config option."""
        opt = SessionConfigOption(
            name="timeout",
            description="Request timeout in seconds",
            value_type="number",
            default_value=30,
        )
        assert opt.name == "timeout"
        assert opt.description == "Request timeout in seconds"
        assert opt.value_type == "number"
        assert opt.default_value == 30

    def test_session_config_option_required_fields(self):
        """Test that name is required."""
        with pytest.raises(ValidationError) as exc_info:
            SessionConfigOption()
        assert "name" in str(exc_info.value)

    def test_session_config_option_with_choices(self):
        """Test session config with choice constraints."""
        opt = SessionConfigOption(
            name="log_level",
            value_type="string",
            choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        )
        assert opt.choices == ["DEBUG", "INFO", "WARNING", "ERROR"]

    def test_session_config_option_defaults(self):
        """Test default values for optional fields."""
        opt = SessionConfigOption(name="test")
        assert opt.description == ""
        assert opt.value_type == "string"
        assert opt.default_value is None
        assert opt.choices is None


class TestModelInfo:
    """Tests for ModelInfo contract."""

    def test_valid_model_info(self):
        """Test creating valid model info."""
        model = ModelInfo(
            name="gpt-4",
            capabilities=["chat", "vision", "function_calling"],
            context_window=8192,
            cost_per_1k_input_tokens=0.03,
            cost_per_1k_output_tokens=0.06,
        )
        assert model.name == "gpt-4"
        assert "vision" in model.capabilities
        assert model.context_window == 8192

    def test_model_info_required_fields(self):
        """Test that name is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelInfo()
        assert "name" in str(exc_info.value)

    def test_model_info_with_capability_flags(self):
        """Test model info with boolean capability flags."""
        model = ModelInfo(
            name="claude-3",
            supports_function_calling=True,
            supports_vision=True,
        )
        assert model.supports_function_calling is True
        assert model.supports_vision is True

    def test_model_info_defaults(self):
        """Test default values."""
        model = ModelInfo(name="gpt-3.5-turbo")
        assert model.capabilities == []
        assert model.context_window is None
        assert model.cost_per_1k_input_tokens is None


class TestMcpCapabilities:
    """Tests for McpCapabilities contract."""

    def test_valid_mcp_capabilities(self):
        """Test creating valid MCP capabilities."""
        caps = McpCapabilities(
            tools={"search": {"description": "Search capability"}},
            resources={"file": {"type": "text"}},
        )
        assert caps.tools is not None
        assert caps.resources is not None
        assert "search" in caps.tools

    def test_mcp_capabilities_all_optional(self):
        """Test that all MCP fields are optional."""
        caps = McpCapabilities()
        assert caps.tools is None
        assert caps.resources is None
        assert caps.prompts is None

    def test_mcp_capabilities_with_sampling(self):
        """Test MCP with sampling capabilities."""
        caps = McpCapabilities(
            sampling={"supported": True, "models": ["gpt-4"]}
        )
        assert caps.sampling is not None
        assert caps.sampling["supported"] is True


class TestAuthMethod:
    """Tests for AuthMethod contract."""

    def test_valid_api_key_auth(self):
        """Test API key authentication method."""
        auth = AuthMethod(
            type="api_key",
            required_fields=["api_key"],
        )
        assert auth.type == "api_key"
        assert "api_key" in auth.required_fields

    def test_oauth2_auth_method(self):
        """Test OAuth2 authentication."""
        auth = AuthMethod(
            type="oauth2",
            required_fields=["client_id", "client_secret"],
            optional_fields=["scope"],
        )
        assert auth.type == "oauth2"
        assert len(auth.required_fields) == 2
        assert "scope" in auth.optional_fields

    def test_auth_method_type_required(self):
        """Test that type is required."""
        with pytest.raises(ValidationError) as exc_info:
            AuthMethod(required_fields=["test"])
        assert "type" in str(exc_info.value)


class TestRequestError:
    """Tests for RequestError contract."""

    def test_valid_request_error(self):
        """Test creating valid request error."""
        error = RequestError(
            code="INVALID_REQUEST",
            message="The request is invalid",
            details={"field": "timeout", "expected": "number"},
        )
        assert error.code == "INVALID_REQUEST"
        assert error.message == "The request is invalid"

    def test_request_error_required_fields(self):
        """Test that code and message are required."""
        with pytest.raises(ValidationError) as exc_info:
            RequestError(code="ERROR")
        assert "message" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            RequestError(message="Error occurred")
        assert "code" in str(exc_info.value)

    def test_request_error_with_details(self):
        """Test error with additional details."""
        error = RequestError(
            code="AUTH_FAILED",
            message="Authentication failed",
            details={"reason": "expired_token", "retry_after": 3600},
        )
        assert error.details["reason"] == "expired_token"


class TestVersionedCredentialBinding:
    """Tests for VersionedCredentialBinding contract."""

    def test_valid_credential_binding(self):
        """Test creating valid credential binding."""
        binding = VersionedCredentialBinding(
            revision=1,
            credentials={"api_key": "sk-xxxxx"},
        )
        assert binding.revision == 1
        assert "api_key" in binding.credentials

    def test_credential_binding_revision_required(self):
        """Test that revision is required."""
        with pytest.raises(ValidationError) as exc_info:
            VersionedCredentialBinding(credentials={})
        assert "revision" in str(exc_info.value)

    def test_credential_binding_with_timestamps(self):
        """Test credential binding with audit timestamps."""
        binding = VersionedCredentialBinding(
            revision=2,
            credentials={"token": "bearer-token"},
            created_at="2026-09-24T00:00:00Z",
            updated_at="2026-09-24T10:30:00Z",
        )
        assert binding.created_at == "2026-09-24T00:00:00Z"
        assert binding.updated_at == "2026-09-24T10:30:00Z"


class TestTraceNode:
    """Tests for TraceNode contract."""

    def test_valid_trace_node(self):
        """Test creating valid trace node."""
        node = TraceNode(
            id="trace-001",
            type="call",
            timestamp="2026-09-24T11:28:00Z",
            duration_ms=125.5,
        )
        assert node.id == "trace-001"
        assert node.type == "call"
        assert node.duration_ms == 125.5

    def test_trace_node_required_fields(self):
        """Test that id, type, and timestamp are required."""
        with pytest.raises(ValidationError):
            TraceNode()

        with pytest.raises(ValidationError):
            TraceNode(id="test", type="call")

    def test_trace_node_with_error(self):
        """Test trace node representing a failure."""
        node = TraceNode(
            id="trace-002",
            type="error",
            timestamp="2026-09-24T11:28:00Z",
            error="Connection timeout",
        )
        assert node.error == "Connection timeout"

    def test_trace_node_hierarchy(self):
        """Test trace node with parent relationship."""
        node = TraceNode(
            id="child-001",
            type="call",
            timestamp="2026-09-24T11:28:00Z",
            parent_id="parent-001",
        )
        assert node.parent_id == "parent-001"


class TestBackgroundTaskSlot:
    """Tests for BackgroundTaskSlot contract."""

    def test_valid_background_task_slot(self):
        """Test creating valid background task slot."""
        slot = BackgroundTaskSlot(
            id="slot-001",
            available=True,
            task_type="file_download",
        )
        assert slot.id == "slot-001"
        assert slot.available is True
        assert slot.task_type == "file_download"

    def test_background_task_slot_id_required(self):
        """Test that id is required."""
        with pytest.raises(ValidationError) as exc_info:
            BackgroundTaskSlot()
        assert "id" in str(exc_info.value)

    def test_background_task_slot_with_current_task(self):
        """Test slot with currently running task."""
        slot = BackgroundTaskSlot(
            id="slot-002",
            available=False,
            current_task_id="task-123",
            max_concurrent=3,
        )
        assert slot.available is False
        assert slot.current_task_id == "task-123"
        assert slot.max_concurrent == 3


class TestAcpSessionState:
    """Tests for AcpSessionState contract."""

    def test_valid_session_state(self):
        """Test creating valid complete session state."""
        state = AcpSessionState(
            session_id="sess-001",
            config_options=[
                SessionConfigOption(name="timeout", value_type="number")
            ],
            models=[ModelInfo(name="gpt-4")],
        )
        assert state.session_id == "sess-001"
        assert len(state.config_options) == 1
        assert len(state.models) == 1

    def test_session_state_session_id_required(self):
        """Test that session_id is required."""
        with pytest.raises(ValidationError) as exc_info:
            AcpSessionState()
        assert "session_id" in str(exc_info.value)

    def test_session_state_with_all_capabilities(self):
        """Test session state with all available capabilities."""
        state = AcpSessionState(
            session_id="sess-002",
            config_options=[],
            models=[],
            mcp_capabilities=McpCapabilities(tools={}),
            auth_method=AuthMethod(type="api_key", required_fields=["key"]),
            trace_nodes=[
                TraceNode(id="t1", type="call", timestamp="2026-09-24T11:28:00Z")
            ],
            background_slots=[BackgroundTaskSlot(id="slot-1")],
        )
        assert state.mcp_capabilities is not None
        assert state.auth_method is not None
        assert len(state.trace_nodes) == 1
        assert len(state.background_slots) == 1

    def test_session_state_defaults(self):
        """Test session state with default empty lists."""
        state = AcpSessionState(session_id="sess-003")
        assert state.config_options == []
        assert state.models == []
        assert state.trace_nodes == []
        assert state.background_slots == []


class TestContractForwardCompatibility:
    """Tests for forward compatibility with extra fields."""

    def test_extra_fields_allowed(self):
        """Test that extra fields are allowed for future ACP versions."""
        model = ModelInfo(
            name="future-model",
            future_capability="supported",  # type: ignore
        )
        assert model.name == "future-model"
        # Extra field is allowed by ConfigDict(extra="allow")

    def test_session_config_extra_fields(self):
        """Test SessionConfigOption allows extra fields."""
        opt = SessionConfigOption(
            name="test",
            experimental_field="value",  # type: ignore
        )
        assert opt.name == "test"
