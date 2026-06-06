import importlib
import warnings


def _resolve(module_name: str, symbol: str):
    module = importlib.import_module(module_name)
    return getattr(module, symbol)


def test_api_index_preferred_imports_resolve():
    documented = {
        "coactra.scope": ["CoactraScope", "Scope", "is_safe_path_component"],
        "coactra.memory": ["Memory", "make_backend", "Scope", "Recollection", "MemoryBackend"],
        "coactra.jobs": ["WorkManager", "WorkOrder", "WorkScope", "Scope", "Orchestrator", "DurableOrchestrator", "Procedure"],
        "coactra.workspace": ["open_workspace", "Workspace", "WorkspaceBackend", "LocalFilesystemBackend", "CliPolicy"],
        "coactra.agent": ["make_agent", "Agent", "Scope", "AIPort", "MemoryPort", "WorkspacePort", "WorkflowPort", "OrganizationPort"],
        "coactra.errors": ["CoactraError", "ErrorCode", "ErrorInfo", "MissingExtraError", "coactra_error_from_exception"],
        "coactra.ai": ["ask", "structured", "Client", "ReasoningEngine", "InMemoryStore"],
        "coactra.directory": ["Organization", "OrgStore", "make_org_store", "Authorizer", "CompanySpec", "bootstrap_company"],
    }
    for module_name, symbols in documented.items():
        for symbol in symbols:
            assert _resolve(module_name, symbol) is not None, (module_name, symbol)


def test_api_index_deprecated_agent_root_imports_resolve_and_warn():
    for symbol in [
        "FakeAI",
        "FakeMemory",
        "FakeWorkspace",
        "FakeWorkflow",
        "FakeOrganization",
        "FakeWork",
        "ToolTrie",
        "build_a2a_app",
    ]:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            assert _resolve("coactra.agent", symbol) is not None
        assert any(item.category is DeprecationWarning for item in caught), symbol
