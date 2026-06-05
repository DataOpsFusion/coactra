from coactra.agent.sdk.events import (
    Assistant, Thinking, ToolCall, ToolResult, Usage, Status, RunResult, Event,
)


def test_events_are_frozen_and_carry_identity():
    ev = Assistant(text="hi", run_id="r1", seq=3)
    assert ev.text == "hi" and ev.run_id == "r1" and ev.seq == 3
    import dataclasses
    try:
        ev.text = "no"  # frozen
        assert False, "expected FrozenInstanceError"
    except dataclasses.FrozenInstanceError:
        pass


def test_tool_call_and_result():
    call = ToolCall(id="t1", name="docs.search", args={"q": "x"}, run_id="r1", seq=1)
    ok = ToolResult(id="t1", name="docs.search", result={"hits": 2}, error=None, run_id="r1", seq=2)
    bad = ToolResult(id="t2", name="docs.search", result=None, error="boom", run_id="r1", seq=3)
    assert call.args["q"] == "x"
    assert ok.error is None and bad.error == "boom"


def test_run_result_factories():
    done = RunResult.finished(text="answer", output=None, usage=Usage(tokens=10, cost=0.0))
    failed = RunResult.failed("timeout")
    assert done.status == "finished" and done.text == "answer"
    assert failed.status == "error" and failed.error == "timeout"
