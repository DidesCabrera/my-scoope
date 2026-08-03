"""Compatibility facade for the AI-owned tool result contract."""

from ai_assistant.domain.tool_results import AIToolError, AIToolResult, tool_error, tool_success

__all__ = ["AIToolError", "AIToolResult", "tool_error", "tool_success"]
