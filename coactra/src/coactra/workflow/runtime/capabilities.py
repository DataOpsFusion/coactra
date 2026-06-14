"""Capability registry contracts for workflow tool execution."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field


def capability_key(server: str, tool: str) -> str:
    return f"{server}.{tool}"


class Capability(BaseModel):
    """Runtime-visible description of one callable tool/capability."""

    server: str = Field(min_length=1)
    tool: str = Field(min_length=1)
    description: str = ""
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] | None = None
    side_effects: bool = False
    timeout_seconds: float | None = Field(default=None, gt=0)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def name(self) -> str:
        return capability_key(self.server, self.tool)

    @property
    def required_inputs(self) -> set[str]:
        required = self.input_schema.get("required", [])
        if not isinstance(required, list):
            return set()
        return {str(item) for item in required}

    def validate_params(self, params: dict[str, Any]) -> list[str]:
        """Return schema-level validation failures for a rendered tool call."""
        failures: list[str] = []
        for key in sorted(self.required_inputs - set(params)):
            failures.append(f"missing required input {key!r}")
        properties = self.input_schema.get("properties", {})
        if not isinstance(properties, dict):
            return failures
        for key, spec in properties.items():
            if key not in params or not isinstance(spec, dict):
                continue
            expected = spec.get("type")
            if expected and not _matches_json_type(params[key], expected):
                failures.append(f"input {key!r} must be {expected!r}")
        return failures


class CapabilityValidationIssue(BaseModel):
    capability: str
    reason: str
    node_id: str | None = None


class CapabilityValidationError(ValueError):
    """Raised when a workflow references unknown or invalid capabilities."""

    def __init__(self, issues: list[CapabilityValidationIssue]) -> None:
        self.issues = issues
        joined = "; ".join(
            f"{issue.node_id or '?'}:{issue.capability}: {issue.reason}" for issue in issues
        )
        super().__init__(joined)


@runtime_checkable
class CapabilityRegistry(Protocol):
    def get(self, server: str, tool: str) -> Capability | None:
        """Return a capability by server/tool name, or None."""
        ...

    def list(self) -> list[Capability]:
        """List registered capabilities."""
        ...


class InMemoryCapabilityRegistry:
    """Simple host-populated registry suitable for tests and local runtimes."""

    def __init__(self, capabilities: list[Capability] | None = None) -> None:
        self._items: dict[str, Capability] = {}
        for capability in capabilities or []:
            self.register(capability)

    def register(self, capability: Capability) -> None:
        self._items[capability.name] = capability

    def get(self, server: str, tool: str) -> Capability | None:
        return self._items.get(capability_key(server, tool))

    def list(self) -> list[Capability]:
        return list(self._items.values())


def require_capability(registry: CapabilityRegistry, server: str, tool: str) -> Capability:
    capability = registry.get(server, tool)
    if capability is None:
        raise CapabilityValidationError(
            [
                CapabilityValidationIssue(
                    capability=capability_key(server, tool),
                    reason="capability is not registered",
                )
            ]
        )
    return capability


def validate_tool_call(
    registry: CapabilityRegistry,
    *,
    server: str,
    tool: str,
    params: dict[str, Any],
    node_id: str | None = None,
) -> Capability:
    capability = require_capability(registry, server, tool)
    failures = capability.validate_params(params)
    if failures:
        raise CapabilityValidationError(
            [
                CapabilityValidationIssue(
                    capability=capability.name,
                    node_id=node_id,
                    reason=failure,
                )
                for failure in failures
            ]
        )
    return capability


def validate_workflow_capabilities(workflow: dict[str, Any], registry: CapabilityRegistry) -> None:
    """Validate tool nodes before graph compilation."""
    issues: list[CapabilityValidationIssue] = []
    for node in workflow.get("nodes", []):
        if node.get("type") != "tool":
            continue
        node_id = str(node.get("id") or "")
        server = node.get("target")
        tool = node.get("tool")
        if not server or not tool:
            issues.append(
                CapabilityValidationIssue(
                    capability="<missing>",
                    node_id=node_id,
                    reason="tool nodes require target and tool",
                )
            )
            continue
        capability = registry.get(str(server), str(tool))
        if capability is None:
            issues.append(
                CapabilityValidationIssue(
                    capability=capability_key(str(server), str(tool)),
                    node_id=node_id,
                    reason="capability is not registered",
                )
            )
            continue
        inputs = node.get("inputs", {})
        if not isinstance(inputs, dict):
            issues.append(
                CapabilityValidationIssue(
                    capability=capability.name,
                    node_id=node_id,
                    reason="inputs must be an object",
                )
            )
            continue
        missing = capability.required_inputs - set(inputs)
        for key in sorted(missing):
            issues.append(
                CapabilityValidationIssue(
                    capability=capability.name,
                    node_id=node_id,
                    reason=f"missing required input {key!r}",
                )
            )
    if issues:
        raise CapabilityValidationError(issues)


def _matches_json_type(value: Any, expected: Any) -> bool:
    if isinstance(expected, list):
        return any(_matches_json_type(value, item) for item in expected)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "null":
        return value is None
    return True


__all__ = [
    "Capability",
    "CapabilityRegistry",
    "CapabilityValidationError",
    "CapabilityValidationIssue",
    "InMemoryCapabilityRegistry",
    "capability_key",
    "require_capability",
    "validate_tool_call",
    "validate_workflow_capabilities",
]
