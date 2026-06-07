import importlib

def _resolve(module_name: str, symbol: str):
    module = importlib.import_module(module_name)
    return getattr(module, symbol)


def test_api_index_preferred_imports_resolve():
    documented = {
        "coactra.scope": ["CoactraScope", "Scope", "is_safe_path_component"],
        "coactra.memory": ["Memory", "make_backend", "Scope", "Recollection", "MemoryBackend"],
        "coactra.workflow": ["WorkManager", "WorkOrder", "WorkScope", "Scope", "Orchestrator", "DurableOrchestrator", "Procedure"],
        "coactra.workspace": ["open_workspace", "Workspace", "WorkspaceBackend", "LocalFilesystemBackend", "CliPolicy"],
        "coactra.agent": ["Scope", "AgentRef", "AllowSameTenant", "AsyncPolicyGatedCollaborator", "CollaborationDenied"],
        "coactra.errors": ["CoactraError", "ErrorCode", "ErrorInfo", "MissingExtraError", "coactra_error_from_exception"],
        "coactra.ai": ["ask", "structured", "Client", "ReasoningEngine", "InMemoryStore"],
        "coactra.team": ["Team", "Organization", "OrgStore", "make_org_store", "Authorizer", "CompanySpec", "bootstrap_company"],
    }
    for module_name, symbols in documented.items():
        for symbol in symbols:
            assert _resolve(module_name, symbol) is not None, (module_name, symbol)


def test_api_index_uses_adapter_imports_for_a2a_server_helpers():
    documented = {
        "coactra.agent.adapters": ["build_a2a_app", "make_a2a_executor"],
    }
    for module_name, symbols in documented.items():
        for symbol in symbols:
            assert _resolve(module_name, symbol) is not None, (module_name, symbol)
