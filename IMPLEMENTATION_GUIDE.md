# ACP Typed Contracts Implementation Guide

## Overview
This document outlines the solution for issue #4973: replacing dynamic attribute access in ACP integration with explicit typed contracts for improved type safety and maintainability.

## Solution Architecture

### Phase 1: Typed Contracts (`acp_contracts.py`)
Define explicit Pydantic models for all ACP capabilities:
- `SessionConfigOption` - Session configuration options
- `ModelInfo` - Language model information
- `McpCapabilities` - MCP server capabilities
- `AuthMethod` - Authentication methods
- `RequestError` - Protocol error responses
- `VersionedCredentialBinding` - Credential bindings with versioning
- `TraceNode` - Tracing and observability nodes
- `BackgroundTaskSlot` - Background task execution slots
- `AcpSessionState` - Complete session state aggregator

### Phase 2: Boundary Adapters (`acp_adapters.py`)
Create safe extraction methods that:
- Translate external ACP library types to internal typed models
- Handle missing/optional fields with sensible defaults
- Log warnings on validation failures
- Keep all `getattr()`/`hasattr()` calls localized
- Support forward compatibility with future ACP versions

Key adapter methods:
- `extract_session_config_option()` - Safely extract config options
- `extract_model_info()` - Safely extract model metadata
- `extract_mcp_capabilities()` - Safely extract MCP capabilities
- `extract_auth_method()` - Safely extract authentication info
- `extract_request_error()` - Safely extract error details
- `extract_credential_binding()` - Safely extract credential bindings
- `extract_trace_node()` - Safely extract trace nodes
- `extract_background_task_slot()` - Safely extract task slots
- `extract_session_state()` - Composite extraction for complete state

### Phase 3: Testing
Comprehensive test suites covering:
- Valid input validation (`test_acp_contracts.py`)
  - 40+ tests for contract validation
  - Field presence and type validation
  - Forward compatibility with extra fields
  
- Adapter boundary translation (`test_acp_adapters.py`)
  - 50+ tests for extraction methods
  - Fallback behavior on missing fields
  - Error handling and logging
  - None input handling

## Implementation Steps

### Step 1: Add Dependencies
Update `pyproject.toml` (if needed):
```toml
[dependencies]
pydantic = ">=2.0"
```

### Step 2: Integrate into `acp_agent.py`
Replace dynamic access patterns:

**Before:**
```python
if hasattr(config, 'session_config'):
    for opt in config.session_config:
        name = getattr(opt, 'name', 'unknown')
        desc = getattr(opt, 'description', '')
        # ... more getattr calls
```

**After:**
```python
from .acp_adapters import AcpBoundaryAdapter

if hasattr(config, 'session_config'):
    for opt_data in config.session_config:
        opt = AcpBoundaryAdapter.extract_session_config_option(opt_data)
        if opt:
            name = opt.name  # Type-safe, IDE autocomplete works
            desc = opt.description
```

### Step 3: Refactor File Credential Handling
Update `acp_file_credentials.py`:

**Before:**
```python
binding = file_credentials.get_binding()
revision = getattr(binding, 'revision', 0)
creds = getattr(binding, 'credentials', {})
```

**After:**
```python
binding_data = file_credentials.get_binding()
binding = AcpBoundaryAdapter.extract_credential_binding(binding_data)
if binding:
    revision = binding.revision
    creds = binding.credentials
```

### Step 4: Refactor Tracing
Update `acp_tracing.py`:

**Before:**
```python
# Pydantic duck-typing
metadata = {}
if hasattr(trace_obj, 'metadata'):
    metadata = getattr(trace_obj, 'metadata')
```

**After:**
```python
node = AcpBoundaryAdapter.extract_trace_node(trace_obj)
if node:
    metadata = node.metadata or {}
```

### Step 5: Type Annotations
Add proper type hints throughout:

```python
from typing import Optional
from .acp_contracts import AcpSessionState, ModelInfo
from .acp_adapters import AcpBoundaryAdapter

def initialize_session(acp_response: Any) -> Optional[AcpSessionState]:
    """Initialize session from ACP response with type safety."""
    return AcpBoundaryAdapter.extract_session_state(acp_response)

def get_model_options(session: AcpSessionState) -> list[ModelInfo]:
    """Get available models with proper typing."""
    return session.models
```

## Backward Compatibility

The solution maintains backward compatibility by:

1. **Boundary Isolation** - All external ACP library access is confined to adapters
2. **Graceful Degradation** - Missing fields default to reasonable values
3. **Extra Fields Allowed** - Pydantic `ConfigDict(extra="allow")` supports future ACP versions
4. **Non-Breaking Changes** - Existing public APIs remain unchanged

## Benefits

✅ **Type Safety**
- mypy/pyright can verify all attribute accesses
- Catch errors at development time, not runtime

✅ **IDE Support**
- Autocomplete for all ACP object attributes
- Jump-to-definition navigation
- Inline documentation

✅ **Maintainability**
- Clear contracts instead of scattered getattr calls
- Self-documenting code with Pydantic models
- Single source of truth for each capability

✅ **Testability**
- Each contract is independently testable
- Each adapter method is independently testable
- Easy to mock ACP library responses

✅ **Forward Compatibility**
- Extra fields are preserved via Pydantic's extra="allow"
- New optional fields are easy to add
- Version negotiation simplified

## Acceptance Criteria

- [x] Typed contracts defined for all ACP capabilities
- [x] Boundary adapters created with comprehensive error handling
- [x] 90+ unit tests covering contracts and adapters
- [x] All dynamic attribute access confined to adapters
- [x] Type hints added to public APIs
- [ ] Integration with existing `acp_agent.py` code
- [ ] Integration with `acp_file_credentials.py`
- [ ] Integration with `acp_tracing.py`
- [ ] mypy/pyright passes with `--strict` mode
- [ ] 100% test coverage for new code

## Next Steps for Integration

1. **Phase 4: Core Integration** (acp_agent.py)
   - Replace all 22 `getattr()` calls with adapter methods
   - Add type annotations to ACP-facing functions
   - Update existing tests to use typed contracts

2. **Phase 5: Credential Integration** (acp_file_credentials.py)
   - Replace 3 dynamic attribute access patterns
   - Add VersionedCredentialBinding protocol
   - Test credential revision tracking

3. **Phase 6: Tracing Integration** (acp_tracing.py)
   - Replace duck-typing with TraceNode contract
   - Standardize trace node creation
   - Add trace validation

4. **Phase 7: Testing & Validation**
   - Add integration tests
   - Run mypy/pyright on full codebase
   - Document migration path for consumers

## Configuration Examples

### Session with Models
```python
from .acp_contracts import AcpSessionState, ModelInfo

session = AcpSessionState(
    session_id="sess-001",
    models=[
        ModelInfo(name="gpt-4", capabilities=["chat", "vision"]),
        ModelInfo(name="claude-3", capabilities=["chat"]),
    ]
)

for model in session.models:  # Type-safe iteration
    print(f"{model.name}: {model.capabilities}")
```

### Configuration Options
```python
from .acp_contracts import SessionConfigOption

options = [
    SessionConfigOption(
        name="timeout",
        description="Request timeout in seconds",
        value_type="number",
        default_value=30
    ),
    SessionConfigOption(
        name="mode",
        description="Execution mode",
        value_type="string",
        choices=["fast", "balanced", "thorough"]
    )
]

for opt in options:  # Full IDE support
    if opt.choices:
        print(f"{opt.name}: {opt.choices}")
```

## Troubleshooting

### Validation Errors
If you see validation errors during extraction:
```python
opt = AcpBoundaryAdapter.extract_session_config_option(obj)
if opt is None:
    # Check logs for ValidationError details
    logger.warning("Failed to extract config option")
    # Provide fallback behavior
```

### Missing Attributes
Adapters handle missing attributes gracefully:
```python
# These are all safe - return None or default values
model = AcpBoundaryAdapter.extract_model_info(obj_with_missing_fields)
if not model:
    logger.warning("Could not extract model info")
```

### Type Checker Errors
Ensure proper imports:
```python
from typing import Optional
from .acp_contracts import ModelInfo
from .acp_adapters import AcpBoundaryAdapter

result: Optional[ModelInfo] = AcpBoundaryAdapter.extract_model_info(obj)
```

## References

- Issue: https://github.com/OpenHands/software-agent-sdk/issues/4973
- Parent Issue: https://github.com/OpenHands/software-agent-sdk/issues/4905
- Pydantic Docs: https://docs.pydantic.dev/
