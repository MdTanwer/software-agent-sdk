"""Boundary adapters for translating external ACP library types to typed contracts.

This module provides safe extraction methods that translate dynamic ACP library
objects into our typed Pydantic models. All dynamic attribute access (getattr/setattr)
should be confined to this module at the ACP integration boundary.
"""

import logging
from typing import Any, Optional

from pydantic import ValidationError

from .acp_contracts import (
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

logger = logging.getLogger(__name__)


class AcpBoundaryAdapter:
    """Safely translate external ACP library types to typed internal contracts.
    
    This adapter is the single point where dynamic attribute access is allowed.
    All getattr/hasattr calls for ACP objects should be here.
    """

    @staticmethod
    def extract_session_config_option(acp_obj: Any) -> Optional[SessionConfigOption]:
        """Safely extract a session configuration option from ACP response.
        
        Args:
            acp_obj: Raw ACP library object (may have any attributes)
            
        Returns:
            Validated SessionConfigOption or None if extraction fails
        """
        if not acp_obj:
            return None
            
        try:
            data = {
                "name": getattr(acp_obj, "name", None),
                "description": getattr(acp_obj, "description", ""),
                "value_type": getattr(acp_obj, "value_type", "string"),
                "default_value": getattr(acp_obj, "default_value", None),
                "choices": getattr(acp_obj, "choices", None),
            }
            # Remove None name as it's required
            if data["name"] is None:
                logger.warning(
                    "SessionConfigOption missing required 'name' field: %s",
                    acp_obj
                )
                return None
            return SessionConfigOption(**data)
        except (ValidationError, AttributeError) as e:
            logger.warning(
                "Failed to extract SessionConfigOption: %s", e
            )
            return None

    @staticmethod
    def extract_model_info(acp_obj: Any) -> Optional[ModelInfo]:
        """Safely extract model information from ACP response.
        
        Args:
            acp_obj: Raw ACP library object
            
        Returns:
            Validated ModelInfo or None if extraction fails
        """
        if not acp_obj:
            return None
            
        try:
            data = {
                "name": getattr(acp_obj, "name", None),
                "capabilities": getattr(acp_obj, "capabilities", []),
                "context_window": getattr(acp_obj, "context_window", None),
                "cost_per_1k_input_tokens": getattr(acp_obj, "cost_per_1k_input_tokens", None),
                "cost_per_1k_output_tokens": getattr(acp_obj, "cost_per_1k_output_tokens", None),
                "supports_function_calling": getattr(acp_obj, "supports_function_calling", None),
                "supports_vision": getattr(acp_obj, "supports_vision", None),
            }
            if data["name"] is None:
                logger.warning("ModelInfo missing required 'name' field: %s", acp_obj)
                return None
            return ModelInfo(**data)
        except (ValidationError, AttributeError) as e:
            logger.warning("Failed to extract ModelInfo: %s", e)
            return None

    @staticmethod
    def extract_mcp_capabilities(acp_obj: Any) -> Optional[McpCapabilities]:
        """Safely extract MCP server capabilities from ACP response.
        
        Args:
            acp_obj: Raw ACP library object
            
        Returns:
            Validated McpCapabilities or None if extraction fails
        """
        if not acp_obj:
            return None
            
        try:
            data = {
                "tools": getattr(acp_obj, "tools", None),
                "resources": getattr(acp_obj, "resources", None),
                "prompts": getattr(acp_obj, "prompts", None),
                "sampling": getattr(acp_obj, "sampling", None),
            }
            return McpCapabilities(**data)
        except (ValidationError, AttributeError) as e:
            logger.warning("Failed to extract McpCapabilities: %s", e)
            return None

    @staticmethod
    def extract_auth_method(acp_obj: Any) -> Optional[AuthMethod]:
        """Safely extract authentication method from ACP response.
        
        Args:
            acp_obj: Raw ACP library object
            
        Returns:
            Validated AuthMethod or None if extraction fails
        """
        if not acp_obj:
            return None
            
        try:
            data = {
                "type": getattr(acp_obj, "type", None),
                "required_fields": getattr(acp_obj, "required_fields", []),
                "optional_fields": getattr(acp_obj, "optional_fields", None),
            }
            if data["type"] is None:
                logger.warning("AuthMethod missing required 'type' field: %s", acp_obj)
                return None
            return AuthMethod(**data)
        except (ValidationError, AttributeError) as e:
            logger.warning("Failed to extract AuthMethod: %s", e)
            return None

    @staticmethod
    def extract_request_error(acp_obj: Any) -> Optional[RequestError]:
        """Safely extract request error from ACP response.
        
        Args:
            acp_obj: Raw ACP library object
            
        Returns:
            Validated RequestError or None if extraction fails
        """
        if not acp_obj:
            return None
            
        try:
            data = {
                "code": getattr(acp_obj, "code", None),
                "message": getattr(acp_obj, "message", None),
                "details": getattr(acp_obj, "details", None),
            }
            if data["code"] is None or data["message"] is None:
                logger.warning(
                    "RequestError missing required fields: %s", acp_obj
                )
                return None
            return RequestError(**data)
        except (ValidationError, AttributeError) as e:
            logger.warning("Failed to extract RequestError: %s", e)
            return None

    @staticmethod
    def extract_credential_binding(acp_obj: Any) -> Optional[VersionedCredentialBinding]:
        """Safely extract credential binding from ACP response.
        
        Args:
            acp_obj: Raw ACP library object
            
        Returns:
            Validated VersionedCredentialBinding or None if extraction fails
        """
        if not acp_obj:
            return None
            
        try:
            data = {
                "revision": getattr(acp_obj, "revision", None),
                "credentials": getattr(acp_obj, "credentials", {}),
                "metadata": getattr(acp_obj, "metadata", None),
                "created_at": getattr(acp_obj, "created_at", None),
                "updated_at": getattr(acp_obj, "updated_at", None),
            }
            if data["revision"] is None:
                logger.warning(
                    "VersionedCredentialBinding missing required 'revision' field: %s",
                    acp_obj
                )
                return None
            return VersionedCredentialBinding(**data)
        except (ValidationError, AttributeError) as e:
            logger.warning("Failed to extract VersionedCredentialBinding: %s", e)
            return None

    @staticmethod
    def extract_trace_node(acp_obj: Any) -> Optional[TraceNode]:
        """Safely extract trace node from ACP logging.
        
        Args:
            acp_obj: Raw ACP library object or dict
            
        Returns:
            Validated TraceNode or None if extraction fails
        """
        if not acp_obj:
            return None
            
        try:
            data = {
                "id": getattr(acp_obj, "id", None),
                "type": getattr(acp_obj, "type", None),
                "timestamp": getattr(acp_obj, "timestamp", None),
                "duration_ms": getattr(acp_obj, "duration_ms", None),
                "metadata": getattr(acp_obj, "metadata", None),
                "parent_id": getattr(acp_obj, "parent_id", None),
                "error": getattr(acp_obj, "error", None),
            }
            if any(v is None for v in [data["id"], data["type"], data["timestamp"]]):
                logger.warning("TraceNode missing required fields: %s", acp_obj)
                return None
            return TraceNode(**data)
        except (ValidationError, AttributeError) as e:
            logger.warning("Failed to extract TraceNode: %s", e)
            return None

    @staticmethod
    def extract_background_task_slot(acp_obj: Any) -> Optional[BackgroundTaskSlot]:
        """Safely extract background task slot from ACP response.
        
        Args:
            acp_obj: Raw ACP library object
            
        Returns:
            Validated BackgroundTaskSlot or None if extraction fails
        """
        if not acp_obj:
            return None
            
        try:
            data = {
                "id": getattr(acp_obj, "id", None),
                "available": getattr(acp_obj, "available", True),
                "task_type": getattr(acp_obj, "task_type", None),
                "current_task_id": getattr(acp_obj, "current_task_id", None),
                "max_concurrent": getattr(acp_obj, "max_concurrent", 1),
            }
            if data["id"] is None:
                logger.warning(
                    "BackgroundTaskSlot missing required 'id' field: %s", acp_obj
                )
                return None
            return BackgroundTaskSlot(**data)
        except (ValidationError, AttributeError) as e:
            logger.warning("Failed to extract BackgroundTaskSlot: %s", e)
            return None

    @staticmethod
    def extract_session_state(acp_obj: Any) -> Optional[AcpSessionState]:
        """Safely extract complete session state from ACP response.
        
        This is the high-level extraction method that combines all other extractors.
        
        Args:
            acp_obj: Raw ACP library object representing session
            
        Returns:
            Validated AcpSessionState or None if extraction fails
        """
        if not acp_obj:
            return None
            
        try:
            # Extract lists
            config_options = []
            if hasattr(acp_obj, "config_options"):
                for opt in getattr(acp_obj, "config_options", []):
                    extracted = AcpBoundaryAdapter.extract_session_config_option(opt)
                    if extracted:
                        config_options.append(extracted)
            
            models = []
            if hasattr(acp_obj, "models"):
                for model in getattr(acp_obj, "models", []):
                    extracted = AcpBoundaryAdapter.extract_model_info(model)
                    if extracted:
                        models.append(extracted)
            
            trace_nodes = []
            if hasattr(acp_obj, "trace_nodes"):
                for node in getattr(acp_obj, "trace_nodes", []):
                    extracted = AcpBoundaryAdapter.extract_trace_node(node)
                    if extracted:
                        trace_nodes.append(extracted)
            
            background_slots = []
            if hasattr(acp_obj, "background_slots"):
                for slot in getattr(acp_obj, "background_slots", []):
                    extracted = AcpBoundaryAdapter.extract_background_task_slot(slot)
                    if extracted:
                        background_slots.append(extracted)
            
            # Extract single objects
            mcp_cap = None
            if hasattr(acp_obj, "mcp_capabilities"):
                mcp_cap = AcpBoundaryAdapter.extract_mcp_capabilities(
                    getattr(acp_obj, "mcp_capabilities")
                )
            
            auth = None
            if hasattr(acp_obj, "auth_method"):
                auth = AcpBoundaryAdapter.extract_auth_method(
                    getattr(acp_obj, "auth_method")
                )
            
            data = {
                "session_id": getattr(acp_obj, "session_id", None),
                "config_options": config_options,
                "models": models,
                "mcp_capabilities": mcp_cap,
                "auth_method": auth,
                "trace_nodes": trace_nodes,
                "background_slots": background_slots,
            }
            
            if data["session_id"] is None:
                logger.warning(
                    "AcpSessionState missing required 'session_id' field: %s", acp_obj
                )
                return None
            
            return AcpSessionState(**data)
        except (ValidationError, AttributeError) as e:
            logger.warning("Failed to extract AcpSessionState: %s", e)
            return None
