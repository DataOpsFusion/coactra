import importlib


def _resolve(module_name: str, symbol: str):
    module = importlib.import_module(module_name)
    return getattr(module, symbol)


def test_api_index_preferred_imports_resolve():
    documented = {
        "coactra.scope": ["Scope", "is_safe_path_component"],
        "coactra.memory": ["Memory", "make_backend", "Scope", "Recollection", "MemoryReader"],
        "coactra.workflow": ["Scope", "Orchestrator", "DurableOrchestrator", "Procedure"],
        "coactra.workflow.ledger": ["WorkManager", "WorkOrder"],
        "coactra.workflow.ledger.domain": ["Scope"],
        "coactra.workspace": [
            "open_workspace",
            "Workspace",
            "WorkspaceBackend",
            "LocalFilesystemBackend",
            "CliPolicy",
        ],
        "coactra.agent": [
            "Scope",
            "AgentRef",
            "AsyncPolicyGatedCollaborator",
            "CollaborationDenied",
        ],
        "coactra.errors": [
            "CoactraError",
            "ErrorCode",
            "ErrorInfo",
            "MissingExtraError",
            "coactra_error_from_exception",
        ],
        "coactra.team": ["Team"],
        "coactra.policy": ["Policy", "PolicyRequest", "Decision", "DecisionOutcome"],
    }
    for module_name, symbols in documented.items():
        for symbol in symbols:
            assert _resolve(module_name, symbol) is not None, (module_name, symbol)


def test_api_index_uses_adapter_imports_for_outbound_a2a():
    documented = {
        "coactra.agent.adapters": ["OfficialA2ATransport", "OfficialA2AClient"],
    }
    for module_name, symbols in documented.items():
        for symbol in symbols:
            assert _resolve(module_name, symbol) is not None, (module_name, symbol)
