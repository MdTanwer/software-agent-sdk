"""Unit tests for ACP boundary adapters."""

from unittest.mock import MagicMock

import pytest

from openhands.sdk.agent.acp_adapters import AcpBoundaryAdapter
from openhands.sdk.agent.acp_contracts import (
    AuthMethod,
    BackgroundTaskSlot,
    McpCapabilities,
    ModelInfo,
    RequestError,
    SessionConfigOption,
    TraceNode,
    VersionedCredentialBinding,
)


class TestSessionConfigOptionExtraction:
    """Tests for extracting session config options from ACP objects."""

    def test_extract_valid_session_config(self):
        """Test extracting valid session config option."""
        acp_obj = MagicMock()
        acp_obj.name = "timeout"
        acp_obj.description = "Request timeout"
        acp_obj.value_type = "number"
        acp_obj.default_value = 30

        result = AcpBoundaryAdapter.extract_session_config_option(acp_obj)

        assert result is not None
        assert result.name == "timeout"
        assert result.description == "Request timeout"
        assert result.value_type == "number"
        assert result.default_value == 30

    def test_extract_config_with_defaults(self):
        """Test extracting config with missing optional fields."""
        acp_obj = MagicMock()
        acp_obj.name = "log_level"
        # Missing description, value_type, default_value, choices
        del acp_obj.description
        del acp_obj.value_type
        del acp_obj.default_value
        del acp_obj.choices

        result = AcpBoundaryAdapter.extract_session_config_option(acp_obj)

        assert result is not None
        assert result.name == "log_level"
        assert result.description == ""  # default
        assert result.value_type == "string"  # default
        assert result.default_value is None

    def test_extract_config_missing_required_field(self):
        """Test extraction fails when required field missing."""
        acp_obj = MagicMock()
        del acp_obj.name  # Missing required field

        result = AcpBoundaryAdapter.extract_session_config_option(acp_obj)

        assert result is None

    def test_extract_config_none_input(self):
        """Test extraction handles None input gracefully."""
        result = AcpBoundaryAdapter.extract_session_config_option(None)
        assert result is None

    def test_extract_config_with_choices(self):
        """Test extracting config with choice constraints."""
        acp_obj = MagicMock()
        acp_obj.name = "mode"
        acp_obj.choices = ["fast", "balanced", "thorough"]

        result = AcpBoundaryAdapter.extract_session_config_option(acp_obj)

        assert result is not None
        assert result.choices == ["fast", "balanced", "thorough"]


class TestModelInfoExtraction:
    """Tests for extracting model info from ACP objects."""

    def test_extract_valid_model_info(self):
        """Test extracting valid model information."""
        acp_obj = MagicMock()
        acp_obj.name = "gpt-4"
        acp_obj.capabilities = ["chat", "vision"]
        acp_obj.context_window = 8192
        acp_obj.cost_per_1k_input_tokens = 0.03

        result = AcpBoundaryAdapter.extract_model_info(acp_obj)

        assert result is not None
        assert result.name == "gpt-4"
        assert "vision" in result.capabilities
        assert result.context_window == 8192
        assert result.cost_per_1k_input_tokens == 0.03

    def test_extract_model_with_capability_flags(self):
        """Test extracting model with boolean capability flags."""
        acp_obj = MagicMock()
        acp_obj.name = "claude-3"
        acp_obj.supports_function_calling = True
        acp_obj.supports_vision = False

        result = AcpBoundaryAdapter.extract_model_info(acp_obj)

        assert result is not None
        assert result.supports_function_calling is True
        assert result.supports_vision is False

    def test_extract_model_missing_name(self):
        """Test extraction fails when name is missing."""
        acp_obj = MagicMock()
        del acp_obj.name

        result = AcpBoundaryAdapter.extract_model_info(acp_obj)

        assert result is None

    def test_extract_model_empty_capabilities(self):
        """Test model with no capabilities."""
        acp_obj = MagicMock()
        acp_obj.name = "basic-model"
        del acp_obj.capabilities

        result = AcpBoundaryAdapter.extract_model_info(acp_obj)

        assert result is not None
        assert result.capabilities == []


class TestMcpCapabilitiesExtraction:
    """Tests for extracting MCP capabilities."""

    def test_extract_valid_mcp_capabilities(self):
        """Test extracting valid MCP capabilities."""
        acp_obj = MagicMock()
        acp_obj.tools = {"search": "description"}
        acp_obj.resources = {"files": "type"}
        acp_obj.prompts = {"templates": "data"}

        result = AcpBoundaryAdapter.extract_mcp_capabilities(acp_obj)

        assert result is not None
        assert result.tools == {"search": "description"}
        assert result.resources == {"files": "type"}
        assert result.prompts == {"templates": "data"}

    def test_extract_mcp_all_optional(self):
        """Test MCP extraction when all fields missing."""
        acp_obj = MagicMock()
        del acp_obj.tools
        del acp_obj.resources
        del acp_obj.prompts

        result = AcpBoundaryAdapter.extract_mcp_capabilities(acp_obj)

        assert result is not None
        assert result.tools is None
        assert result.resources is None
        assert result.prompts is None

    def test_extract_mcp_with_sampling(self):
        """Test MCP with sampling capabilities."""
        acp_obj = MagicMock()
        acp_obj.sampling = {"models": ["gpt-4", "claude"]}

        result = AcpBoundaryAdapter.extract_mcp_capabilities(acp_obj)

        assert result is not None
        assert result.sampling == {"models": ["gpt-4", "claude"]}


class TestAuthMethodExtraction:
    """Tests for extracting authentication methods."""

    def test_extract_api_key_auth(self):
        """Test extracting API key auth method."""
        acp_obj = MagicMock()
        acp_obj.type = "api_key"
        acp_obj.required_fields = ["api_key"]
        acp_obj.optional_fields = ["api_version"]

        result = AcpBoundaryAdapter.extract_auth_method(acp_obj)

        assert result is not None
        assert result.type == "api_key"
        assert "api_key" in result.required_fields
        assert "api_version" in result.optional_fields

    def test_extract_oauth2_auth(self):
        """Test extracting OAuth2 auth method."""
        acp_obj = MagicMock()
        acp_obj.type = "oauth2"
        acp_obj.required_fields = ["client_id", "client_secret"]

        result = AcpBoundaryAdapter.extract_auth_method(acp_obj)

        assert result is not None
        assert result.type == "oauth2"
        assert len(result.required_fields) == 2

    def test_extract_auth_missing_type(self):
        """Test extraction fails when type is missing."""
        acp_obj = MagicMock()
        del acp_obj.type
        acp_obj.required_fields = []

        result = AcpBoundaryAdapter.extract_auth_method(acp_obj)

        assert result is None


class TestRequestErrorExtraction:
    """Tests for extracting request errors."""

    def test_extract_valid_request_error(self):
        """Test extracting valid request error."""
        acp_obj = MagicMock()
        acp_obj.code = "INVALID_REQUEST"
        acp_obj.message = "Request is invalid"
        acp_obj.details = {"field": "timeout"}

        result = AcpBoundaryAdapter.extract_request_error(acp_obj)

        assert result is not None
        assert result.code == "INVALID_REQUEST"
        assert result.message == "Request is invalid"
        assert result.details == {"field": "timeout"}

    def test_extract_error_missing_code(self):
        """Test extraction fails when code is missing."""
        acp_obj = MagicMock()
        del acp_obj.code
        acp_obj.message = "Error"

        result = AcpBoundaryAdapter.extract_request_error(acp_obj)

        assert result is None

    def test_extract_error_missing_message(self):
        """Test extraction fails when message is missing."""
        acp_obj = MagicMock()
        acp_obj.code = "ERROR"
        del acp_obj.message

        result = AcpBoundaryAdapter.extract_request_error(acp_obj)

        assert result is None


class TestCredentialBindingExtraction:
    """Tests for extracting credential bindings."""

    def test_extract_valid_credential_binding(self):
        """Test extracting valid credential binding."""
        acp_obj = MagicMock()
        acp_obj.revision = 1
        acp_obj.credentials = {"api_key": "secret"}
        acp_obj.metadata = {"service": "openai"}
        acp_obj.created_at = "2026-09-24T00:00:00Z"

        result = AcpBoundaryAdapter.extract_credential_binding(acp_obj)

        assert result is not None
        assert result.revision == 1
        assert result.credentials == {"api_key": "secret"}
        assert result.metadata == {"service": "openai"}
        assert result.created_at == "2026-09-24T00:00:00Z"

    def test_extract_binding_missing_revision(self):
        """Test extraction fails when revision is missing."""
        acp_obj = MagicMock()
        del acp_obj.revision
        acp_obj.credentials = {}

        result = AcpBoundaryAdapter.extract_credential_binding(acp_obj)

        assert result is None

    def test_extract_binding_versioning(self):
        """Test credential binding with multiple revisions."""
        for rev in [1, 2, 3]:
            acp_obj = MagicMock()
            acp_obj.revision = rev
            acp_obj.credentials = {"key": f"value-v{rev}"}
            acp_obj.updated_at = f"2026-09-24T{rev:02d}:00:00Z"

            result = AcpBoundaryAdapter.extract_credential_binding(acp_obj)

            assert result is not None
            assert result.revision == rev


class TestTraceNodeExtraction:
    """Tests for extracting trace nodes."""

    def test_extract_valid_trace_node(self):
        """Test extracting valid trace node."""
        acp_obj = MagicMock()
        acp_obj.id = "trace-001"
        acp_obj.type = "call"
        acp_obj.timestamp = "2026-09-24T11:28:00Z"
        acp_obj.duration_ms = 125.5
        acp_obj.metadata = {"function": "search"}

        result = AcpBoundaryAdapter.extract_trace_node(acp_obj)

        assert result is not None
        assert result.id == "trace-001"
        assert result.type == "call"
        assert result.duration_ms == 125.5

    def test_extract_error_trace_node(self):
        """Test extracting trace node representing error."""
        acp_obj = MagicMock()
        acp_obj.id = "trace-002"
        acp_obj.type = "error"
        acp_obj.timestamp = "2026-09-24T11:28:00Z"
        acp_obj.error = "Connection timeout"
        acp_obj.parent_id = "trace-001"

        result = AcpBoundaryAdapter.extract_trace_node(acp_obj)

        assert result is not None
        assert result.type == "error"
        assert result.error == "Connection timeout"
        assert result.parent_id == "trace-001"

    def test_extract_trace_missing_required_field(self):
        """Test extraction fails with missing required fields."""
        acp_obj = MagicMock()
        acp_obj.id = "trace-003"
        del acp_obj.type

        result = AcpBoundaryAdapter.extract_trace_node(acp_obj)

        assert result is None


class TestBackgroundTaskSlotExtraction:
    """Tests for extracting background task slots."""

    def test_extract_valid_task_slot(self):
        """Test extracting valid background task slot."""
        acp_obj = MagicMock()
        acp_obj.id = "slot-001"
        acp_obj.available = True
        acp_obj.task_type = "file_download"
        acp_obj.max_concurrent = 3

        result = AcpBoundaryAdapter.extract_background_task_slot(acp_obj)

        assert result is not None
        assert result.id == "slot-001"
        assert result.available is True
        assert result.task_type == "file_download"
        assert result.max_concurrent == 3

    def test_extract_slot_with_current_task(self):
        """Test extracting slot with running task."""
        acp_obj = MagicMock()
        acp_obj.id = "slot-002"
        acp_obj.available = False
        acp_obj.current_task_id = "task-123"

        result = AcpBoundaryAdapter.extract_background_task_slot(acp_obj)

        assert result is not None
        assert result.available is False
        assert result.current_task_id == "task-123"

    def test_extract_slot_missing_id(self):
        """Test extraction fails when id is missing."""
        acp_obj = MagicMock()
        del acp_obj.id

        result = AcpBoundaryAdapter.extract_background_task_slot(acp_obj)

        assert result is None


class TestSessionStateExtraction:
    """Tests for extracting complete session state."""

    def test_extract_valid_session_state(self):
        """Test extracting valid complete session state."""
        acp_obj = MagicMock()
        acp_obj.session_id = "sess-001"

        # Mock lists
        config_opt = MagicMock()
        config_opt.name = "timeout"
        acp_obj.config_options = [config_opt]

        model_obj = MagicMock()
        model_obj.name = "gpt-4"
        acp_obj.models = [model_obj]

        acp_obj.trace_nodes = []
        acp_obj.background_slots = []

        # Mock single objects
        auth_obj = MagicMock()
        auth_obj.type = "api_key"
        auth_obj.required_fields = ["key"]
        acp_obj.auth_method = auth_obj

        acp_obj.mcp_capabilities = None

        result = AcpBoundaryAdapter.extract_session_state(acp_obj)

        assert result is not None
        assert result.session_id == "sess-001"
        assert len(result.config_options) == 1
        assert len(result.models) == 1
        assert result.auth_method is not None

    def test_extract_session_missing_session_id(self):
        """Test extraction fails without session_id."""
        acp_obj = MagicMock()
        del acp_obj.session_id

        result = AcpBoundaryAdapter.extract_session_state(acp_obj)

        assert result is None

    def test_extract_session_empty_lists(self):
        """Test extraction with empty resource lists."""
        acp_obj = MagicMock()
        acp_obj.session_id = "sess-002"
        acp_obj.config_options = []
        acp_obj.models = []
        acp_obj.trace_nodes = []
        acp_obj.background_slots = []

        result = AcpBoundaryAdapter.extract_session_state(acp_obj)

        assert result is not None
        assert result.config_options == []
        assert result.models == []

    def test_extract_session_with_partial_resources(self):
        """Test extraction when some resources are missing."""
        acp_obj = MagicMock()
        acp_obj.session_id = "sess-003"
        del acp_obj.config_options  # Missing this
        acp_obj.models = []
        del acp_obj.trace_nodes  # Missing this
        acp_obj.background_slots = []

        result = AcpBoundaryAdapter.extract_session_state(acp_obj)

        assert result is not None
        assert result.config_options == []  # Should default to empty
        assert result.trace_nodes == []  # Should default to empty


class TestAdapterErrorHandling:
    """Tests for error handling across all adapters."""

    def test_adapter_logs_on_validation_error(self, caplog):
        """Test that adapters log validation errors."""
        acp_obj = MagicMock()
        acp_obj.name = "test"
        acp_obj.revision = "not-a-number"  # Will fail validation

        # Should not raise, but log a warning
        result = AcpBoundaryAdapter.extract_credential_binding(acp_obj)

        assert result is None

    def test_adapter_handles_attribute_error(self):
        """Test adapter handles AttributeError gracefully."""
        # Object without __getattr__ support
        acp_obj = object()

        result = AcpBoundaryAdapter.extract_model_info(acp_obj)

        assert result is None

    def test_all_adapters_handle_none_input(self):
        """Test all adapter methods handle None input."""
        adapters = [
            AcpBoundaryAdapter.extract_session_config_option,
            AcpBoundaryAdapter.extract_model_info,
            AcpBoundaryAdapter.extract_mcp_capabilities,
            AcpBoundaryAdapter.extract_auth_method,
            AcpBoundaryAdapter.extract_request_error,
            AcpBoundaryAdapter.extract_credential_binding,
            AcpBoundaryAdapter.extract_trace_node,
            AcpBoundaryAdapter.extract_background_task_slot,
            AcpBoundaryAdapter.extract_session_state,
        ]

        for adapter in adapters:
            result = adapter(None)
            assert result is None, f"{adapter.__name__} should handle None input"
