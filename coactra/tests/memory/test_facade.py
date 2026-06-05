"""Facade tests — async surface AND the sync bridge, over the in-process backend."""

import asyncio

import pytest

from coactra.memory import ExportReport, Memory, Recollection, Scope, make_backend

SCOPE = Scope(tenant="acme", agent="agent1")


async def test_async_remember_recall_returns_recollections():
    mem = Memory(backend=make_backend("inprocess"))
    await mem.remember(["the build broke on the linter step"], SCOPE)
    hits = await mem.recall("why did the build break", SCOPE, k=5)
    assert hits
    assert isinstance(hits[0], Recollection)
    assert "build broke" in hits[0].text


async def test_async_export_moves_scope_into_another_backend():
    src = make_backend("inprocess")
    dst = make_backend("inprocess")
    mem = Memory(backend=src)
    await mem.remember(["a portable lesson"], SCOPE)

    report = await mem.export(to=dst, scope=SCOPE)
    assert isinstance(report, ExportReport)
    assert report.transferred == 1
    assert {r.text for r in await dst.dump(SCOPE)} == {"a portable lesson"}


def test_sync_bridge_remember_recall_from_plain_sync_caller():
    mem = Memory(backend=make_backend("inprocess"))
    mem.sync.remember(["deploy decision: use blue-green"], SCOPE)
    hits = mem.sync.recall("deploy decision", SCOPE, k=3)
    assert hits and "blue-green" in hits[0].text


def test_sync_bridge_export():
    src = make_backend("inprocess")
    dst = make_backend("inprocess")
    mem = Memory(backend=src)
    mem.sync.remember(["x"], SCOPE)
    report = mem.sync.export(to=dst, scope=SCOPE)
    assert report.transferred == 1


def test_sync_bridge_raises_inside_running_loop():
    # asyncio.run cannot be nested — sync bridge is for sync callers only.
    async def _inner():
        Memory(backend=make_backend("inprocess")).sync.recall("q", SCOPE)

    with pytest.raises(RuntimeError):
        asyncio.run(_inner())


async def test_sync_bridge_guard_message_from_running_loop():
    # This test body itself runs inside a live event loop (async-auto), so the guard
    # must fire. Assert it raises OUR clear message ("await the async ...") and NOT
    # asyncio's generic nested-run error — that is the whole point of the guard.
    mem = Memory(backend=make_backend("inprocess"))
    with pytest.raises(RuntimeError, match="await the async"):
        mem.sync.recall("q", SCOPE)
