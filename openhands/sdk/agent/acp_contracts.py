"""Typed contracts for ACP (Agent Capability Protocol) capabilities.

This module defines explicit Pydantic models for each ACP capability,
replacing dynamic attribute access with strongly-typed contracts.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class AcpCapabilityContract(BaseModel):
    """Base contract for all ACP capabilities.
    
    Allows extra fields for forward compatibility with future ACP versions.
    """
    model_config = ConfigDict(extra="allow")


class SessionConfigOption(AcpCapabilityContract):
    """Contract for session configuration options.
    
    Represents a single configuration option available in an ACP session.
    """
    name: str = Field(..., description="Configuration option name")
    description: str = Field(default="", description="Human-readable description")
    value_type: str = Field(default="string", description="Type of value (boolean, string, number, etc.)")
    default_value: Optional[Any] = Field(default=None, description="Default value if not specified")
    choices: Optional[List[str]] = Field(default=None, description="Valid choices if constrained")


class ModelInfo(AcpCapabilityContract):
    """Contract for model information.
    
    Represents metadata about a language model available through ACP.
    """
    name: str = Field(..., description="Model name/identifier")
    capabilities: List[str] = Field(default_factory=list, description="List of capabilities (vision, tools, etc.)")
    context_window: Optional[int] = Field(default=None, description="Maximum context window in tokens")
    cost_per_1k_input_tokens: Optional[float] = Field(default=None, description="Cost per 1K input tokens")
    cost_per_1k_output_tokens: Optional[float] = Field(default=None, description="Cost per 1K output tokens")
    supports_function_calling: Optional[bool] = Field(default=None, description="Whether model supports function calling")
    supports_vision: Optional[bool] = Field(default=None, description="Whether model supports vision/images")


class McpCapabilities(AcpCapabilityContract):
    """Contract for MCP (Model Context Protocol) server capabilities.
    
    Represents what tools, resources, and prompts an MCP server exposes.
    """
    tools: Optional[Dict[str, Any]] = Field(default=None, description="Available tools")
    resources: Optional[Dict[str, Any]] = Field(default=None, description="Available resources")
    prompts: Optional[Dict[str, Any]] = Field(default=None, description="Available prompts")
    sampling: Optional[Dict[str, Any]] = Field(default=None, description="Sampling capabilities")


class AuthMethod(AcpCapabilityContract):
    """Contract for authentication methods.
    
    Specifies how to authenticate with an ACP provider.
    """
    type: str = Field(..., description="Auth type (api_key, oauth2, basic, bearer, etc.)")
    required_fields: List[str] = Field(default_factory=list, description="Required credential fields")
    optional_fields: Optional[List[str]] = Field(default=None, description="Optional credential fields")


class RequestError(AcpCapabilityContract):
    """Contract for ACP request errors.
    
    Standardized error information from ACP protocol responses.
    """
    code: str = Field(..., description="Error code/type")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional error details")


class VersionedCredentialBinding(AcpCapabilityContract):
    """Contract for versioned credential bindings.
    
    Represents a credential binding with revision tracking.
    """
    revision: int = Field(..., description="Revision number of the binding")
    credentials: Dict[str, Any] = Field(default_factory=dict, description="The actual credentials")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional binding metadata")
    created_at: Optional[str] = Field(default=None, description="ISO 8601 creation timestamp")
    updated_at: Optional[str] = Field(default=None, description="ISO 8601 last update timestamp")


class TraceNode(AcpCapabilityContract):
    """Contract for tracing/logging nodes.
    
    Represents a single node in a trace tree for debugging and observability.
    """
    id: str = Field(..., description="Unique node identifier")
    type: str = Field(..., description="Node type (call, return, error, etc.)")
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    duration_ms: Optional[float] = Field(default=None, description="Duration in milliseconds")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")
    parent_id: Optional[str] = Field(default=None, description="Parent node ID if nested")
    error: Optional[str] = Field(default=None, description="Error message if failed")


class BackgroundTaskSlot(AcpCapabilityContract):
    """Contract for background task execution slots.
    
    Represents a slot available for background task execution.
    """
    id: str = Field(..., description="Slot identifier")
    available: bool = Field(default=True, description="Whether slot is available")
    task_type: Optional[str] = Field(default=None, description="Type of task this slot handles")
    current_task_id: Optional[str] = Field(default=None, description="ID of currently running task if any")
    max_concurrent: Optional[int] = Field(default=1, description="Max concurrent tasks in this slot")


class AcpSessionState(AcpCapabilityContract):
    """Contract for ACP session state.
    
    Complete view of an active ACP session's configuration and capabilities.
    """
    session_id: str = Field(..., description="Unique session identifier")
    config_options: List[SessionConfigOption] = Field(default_factory=list, description="Available config options")
    models: List[ModelInfo] = Field(default_factory=list, description="Available models")
    mcp_capabilities: Optional[McpCapabilities] = Field(default=None, description="MCP server capabilities")
    auth_method: Optional[AuthMethod] = Field(default=None, description="Authentication method")
    trace_nodes: List[TraceNode] = Field(default_factory=list, description="Trace history")
    background_slots: List[BackgroundTaskSlot] = Field(default_factory=list, description="Available background task slots")
