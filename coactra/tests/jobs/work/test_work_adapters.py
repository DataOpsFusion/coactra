from types import SimpleNamespace

import pytest

from coactra.jobs import Scope, WorkOrder
from coactra.jobs.work import (
    AgentSpec,
    Artifact,
    ArtifactPart,
    ArtifactRef,
    EventEnvelope,
    SkillSpec,
)
from coactra.jobs.work.adapters import (
    DaprDispatcher,
    DBOSDispatcher,
    FsspecArtifactStore,
    OpenTelemetryAuditSink,
    TemporalDispatcher,
    to_a2a_agent_card,
    to_a2a_artifact,
    to_cloudevent,
)


class Struct:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


A2A_TYPES = SimpleNamespace(
    AgentCapabilities=Struct,
    AgentCard=Struct,
    AgentSkill=Struct,
    Artifact=Struct,
    DataPart=Struct,
    FilePart=Struct,
    FileWithUri=Struct,
    Part=Struct,
    TextPart=Struct,
)


class DBOSHandle:
    def __init__(self, work_id="work-1") -> None:
        self.work_id = work_id

    def get_workflow_id(self):
        return self.work_id

    def get_status(self):
        return "ENQUEUED"

    def get_result(self):
        return {"ok": True}


class DBOSClient:
    def __init__(self) -> None:
        self.calls = []

    def enqueue(self, options, *args, **kwargs):
        self.calls.append(("enqueue", options, args, kwargs))
        return DBOSHandle(options["workflow_id"])

    def retrieve_workflow(self, work_id):
        self.calls.append(("retrieve", work_id))
        return DBOSHandle(work_id)

    def cancel_workflow(self, work_id):
        self.calls.append(("cancel", work_id))

    def resume_workflow(self, work_id, **kwargs):
        self.calls.append(("resume", work_id, kwargs))
        return DBOSHandle(work_id)

    def fork_workflow(self, work_id, start_step, **kwargs):
        self.calls.append(("fork", work_id, start_step, kwargs))
        return DBOSHandle("forked")

    def send(self, work_id, message, **kwargs):
        self.calls.append(("send", work_id, message, kwargs))


def test_dbos_dispatcher_maps_work_order_to_registered_queue():
    client = DBOSClient()
    dispatcher = DBOSDispatcher(
        client,
        workflow_name="jobs.process",
        queue_name="agent-work",
        partition_by_scope=True,
    )
    order = WorkOrder(
        id="work-1",
        scope=Scope(tenant_id="acme", namespace="ops"),
        title="Process incident",
        idempotency_key="event-42",
    )

    assert dispatcher.submit(order, "extra") == "work-1"
    _, options, args, _ = client.calls[0]
    assert options == {
        "workflow_name": "jobs.process",
        "queue_name": "agent-work",
        "workflow_id": "work-1",
        "deduplication_id": "event-42",
        "queue_partition_key": "acme/ops",
    }
    assert args[0]["title"] == "Process incident"
    assert args[1] == "extra"

    assert dispatcher.status("work-1") == "ENQUEUED"
    assert dispatcher.result("work-1") == {"ok": True}
    dispatcher.cancel("work-1")
    dispatcher.resume("work-1")
    dispatcher.fork("work-1", start_step=2)
    dispatcher.send("work-1", {"approved": True}, topic="approval")


class TemporalHandle:
    def __init__(self) -> None:
        self.calls = []

    async def cancel(self):
        self.calls.append(("cancel",))

    async def signal(self, *args):
        self.calls.append(("signal", *args))

    async def result(self):
        self.calls.append(("result",))
        return "done"


class TemporalClient:
    def __init__(self) -> None:
        self.calls = []
        self.workflow_handle = TemporalHandle()

    async def start_workflow(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return self.workflow_handle

    def get_workflow_handle(self, work_id):
        self.calls.append(("handle", work_id))
        return self.workflow_handle


@pytest.mark.asyncio
async def test_temporal_dispatcher_uses_work_id_and_task_queue():
    client = TemporalClient()
    dispatcher = TemporalDispatcher(client, workflow="RunWork", task_queue="agent-work")
    order = WorkOrder(id="work-1", scope=Scope(tenant_id="acme"), title="Process incident")

    assert await dispatcher.submit(order) is client.workflow_handle
    args, kwargs = client.calls[0]
    assert args[0] == "RunWork"
    assert args[1]["scope"] == {"tenant_id": "acme", "namespace": "default"}
    assert kwargs == {"id": "work-1", "task_queue": "agent-work"}
    await dispatcher.signal("work-1", "approve", {"ok": True})
    await dispatcher.cancel("work-1")
    assert await dispatcher.result("work-1") == "done"


def test_a2a_converter_uses_official_sdk_shapes():
    card = to_a2a_agent_card(
        AgentSpec(
            id="analyst",
            name="Analyst",
            skills=[SkillSpec(id="research", name="Research", tags=["web"])],
        ),
        url="https://agents.example/analyst",
        version="1.0.0",
        types=A2A_TYPES,
    )
    assert card.name == "Analyst"
    assert card.skills[0].id == "research"
    assert card.capabilities.stateTransitionHistory is True

    artifact = to_a2a_artifact(
        Artifact(
            name="report",
            parts=[
                ArtifactPart(kind="text", text="summary"),
                ArtifactPart(kind="data", data={"score": 1}),
                ArtifactPart(
                    kind="reference",
                    reference=ArtifactRef(uri="s3://reports/1", media_type="text/markdown"),
                ),
            ],
        ),
        types=A2A_TYPES,
    )
    assert artifact.parts[0].root.text == "summary"
    assert artifact.parts[1].root.data == {"score": 1}
    assert artifact.parts[2].root.file.uri == "s3://reports/1"


class CloudEvent:
    def __init__(self, attributes, data):
        self.attributes = attributes
        self.data = data


def test_cloudevents_converter_uses_sdk_constructor(monkeypatch):
    from coactra.jobs.work.adapters import cloudevents

    monkeypatch.setattr(
        cloudevents,
        "optional_module",
        lambda *args, **kwargs: SimpleNamespace(CloudEvent=CloudEvent),
    )
    converted = to_cloudevent(EventEnvelope(type="coactra.jobs.started", tenant_id="acme"))
    assert converted.attributes["specversion"] == "1.0"
    assert converted.data == {}

class Span:
    def __init__(self):
        self.events = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def add_event(self, name, attributes):
        self.events.append((name, attributes))


class Tracer:
    def __init__(self):
        self.calls = []
        self.span = Span()

    def start_as_current_span(self, name, attributes):
        self.calls.append((name, attributes))
        return self.span


def test_opentelemetry_sink_emits_lifecycle_span_and_scalar_event_attributes():
    tracer = Tracer()
    sink = OpenTelemetryAuditSink(tracer)
    sink.emit(
        EventEnvelope(
            type="coactra.jobs.completed",
            tenant_id="acme",
            subject="work-1",
            data={"status": "completed", "nested": {"drop": True}},
        )
    )
    assert tracer.calls[0][0] == "coactra.jobs.completed"
    assert tracer.span.events == [("coactra.jobs.completed", {"status": "completed"})]


class DaprClient:
    def __init__(self):
        self.calls = []

    def schedule_new_workflow(self, **kwargs):
        self.calls.append(("submit", kwargs))
        return kwargs["instance_id"]

    def get_workflow_state(self, **kwargs):
        self.calls.append(("status", kwargs))
        return "RUNNING"

    def pause_workflow(self, **kwargs):
        self.calls.append(("pause", kwargs))

    def resume_workflow(self, **kwargs):
        self.calls.append(("resume", kwargs))

    def raise_workflow_event(self, **kwargs):
        self.calls.append(("signal", kwargs))

    def terminate_workflow(self, **kwargs):
        self.calls.append(("cancel", kwargs))

    def purge_workflow(self, **kwargs):
        self.calls.append(("purge", kwargs))


def test_dapr_dispatcher_maps_work_order_to_workflow_instance():
    client = DaprClient()
    dispatcher = DaprDispatcher(client, workflow="RunWork")
    order = WorkOrder(id="work-1", scope=Scope(tenant_id="acme"), title="Process incident")

    assert dispatcher.submit(order) == "work-1"
    assert client.calls[0][1]["workflow"] == "RunWork"
    assert client.calls[0][1]["input"]["title"] == "Process incident"
    assert dispatcher.status("work-1") == "RUNNING"
    dispatcher.pause("work-1")
    dispatcher.resume("work-1")
    dispatcher.signal("work-1", "approval", {"accepted": True})
    dispatcher.cancel("work-1")
    dispatcher.purge("work-1")


class MemoryFile:
    def __init__(self, fs, path, mode):
        import io

        self.fs = fs
        self.path = path
        self.mode = mode
        self.buffer = io.StringIO(fs.files.get(path, ""))

    def __enter__(self):
        return self.buffer

    def __exit__(self, *args):
        if "w" in self.mode:
            self.fs.files[self.path] = self.buffer.getvalue()
        self.buffer.close()


class MemoryFS:
    def __init__(self):
        self.files = {}

    def makedirs(self, path, exist_ok=False):
        return None

    def open(self, path, mode):
        return MemoryFile(self, path, mode)


def test_fsspec_artifact_store_is_scope_isolated():
    fs = MemoryFS()
    store = FsspecArtifactStore("memory://coactra", fs=fs)
    scope = Scope(tenant_id="acme", namespace="support")
    artifact = Artifact(name="report", parts=[ArtifactPart(kind="text", text="done")])

    reference = store.put(artifact, scope)
    assert store.get(reference, scope) == artifact
    with pytest.raises(ValueError):
        store.get(reference, Scope(tenant_id="globex", namespace="support"))


def test_fsspec_artifact_store_rejects_nested_reference_paths():
    fs = MemoryFS()
    store = FsspecArtifactStore("memory://coactra", fs=fs)
    scope = Scope(tenant_id="acme", namespace="support")
    reference = ArtifactRef(
        uri="memory://coactra/acme/support/artifacts/../private/report.json"
    )

    with pytest.raises(ValueError, match="scoped artifact envelope"):
        store.get(reference, scope)
