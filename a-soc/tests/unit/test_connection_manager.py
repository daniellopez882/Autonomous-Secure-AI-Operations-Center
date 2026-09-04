"""
Regression tests for core.realtime.ConnectionManager.

The defect these pin: broadcast was

    for connection in self.active_connections:
        await connection.send_json(message)

so one dead client aborted the loop and every client after it in the list got
nothing. The dead socket was never pruned, so it broke every later broadcast
too.

The consequence was worse than a dropped message. ``background_telemetry()``
calls broadcast inside ``while True`` with no exception handling, so the first
raised error ended that task for the lifetime of the process: the live feed
stopped for everyone the first time a single browser tab closed.
"""

from __future__ import annotations

import asyncio

import pytest

from core.realtime.connection_manager import ConnectionManager


class LiveSocket:
    def __init__(self) -> None:
        self.received: list[dict] = []
        self.closed = False

    async def send_json(self, data: dict) -> None:
        self.received.append(data)

    async def accept(self) -> None:
        pass

    async def close(self) -> None:
        self.closed = True


class DeadSocket:
    """Raises the way a WebSocket does once the peer has gone."""

    async def send_json(self, data: dict) -> None:
        raise RuntimeError("Cannot call send once a close message has been sent.")

    async def accept(self) -> None:
        pass


class SlowSocket:
    def __init__(self, delay: float = 10.0) -> None:
        self.delay = delay

    async def send_json(self, data: dict) -> None:
        await asyncio.sleep(self.delay)

    async def accept(self) -> None:
        pass


@pytest.mark.asyncio
class TestBroadcastResilience:
    async def test_dead_client_does_not_starve_the_others(self):
        """The regression: everyone after the dead socket received nothing."""
        m = ConnectionManager()
        dead, live_a, live_b = DeadSocket(), LiveSocket(), LiveSocket()
        m.active_connections = [dead, live_a, live_b]

        delivered = await m.broadcast({"seq": 1})

        assert delivered == 2
        assert live_a.received == [{"seq": 1}]
        assert live_b.received == [{"seq": 1}]

    async def test_broadcast_never_raises(self):
        m = ConnectionManager()
        m.active_connections = [DeadSocket(), DeadSocket()]
        assert await m.broadcast({"a": 1}) == 0

    async def test_dead_client_is_pruned(self):
        m = ConnectionManager()
        dead, live = DeadSocket(), LiveSocket()
        m.active_connections = [dead, live]

        await m.broadcast({"seq": 1})

        assert dead not in m.active_connections
        assert live in m.active_connections
        assert len(m) == 1

    async def test_later_broadcasts_are_unaffected(self):
        """The dead socket used to poison every subsequent broadcast."""
        m = ConnectionManager()
        live = LiveSocket()
        m.active_connections = [DeadSocket(), live]

        await m.broadcast({"seq": 1})
        await m.broadcast({"seq": 2})
        await m.broadcast({"seq": 3})

        assert live.received == [{"seq": 1}, {"seq": 2}, {"seq": 3}]

    async def test_a_hung_client_cannot_stall_the_fanout(self):
        m = ConnectionManager(send_timeout=0.05)
        slow, live = SlowSocket(delay=5.0), LiveSocket()
        m.active_connections = [slow, live]

        delivered = await asyncio.wait_for(m.broadcast({"seq": 1}), timeout=2.0)

        assert delivered == 1
        assert live.received == [{"seq": 1}]
        assert slow not in m.active_connections

    async def test_broadcast_with_no_clients_is_a_noop(self):
        assert await ConnectionManager().broadcast({"a": 1}) == 0


@pytest.mark.asyncio
class TestDisconnect:
    async def test_disconnecting_an_unknown_socket_does_not_raise(self):
        """Regression: list.remove() raised ValueError."""
        ConnectionManager().disconnect(LiveSocket())

    async def test_disconnect_removes_the_socket(self):
        m = ConnectionManager()
        s = LiveSocket()
        await m.connect(s)
        assert len(m) == 1
        m.disconnect(s)
        assert len(m) == 0

    async def test_double_disconnect_is_safe(self):
        m = ConnectionManager()
        s = LiveSocket()
        await m.connect(s)
        m.disconnect(s)
        m.disconnect(s)
        assert len(m) == 0


@pytest.mark.asyncio
class TestLifecycle:
    async def test_connect_accepts_and_registers(self):
        m = ConnectionManager()
        s = LiveSocket()
        await m.connect(s)
        assert s in m.active_connections

    async def test_close_all_clears_registry(self):
        m = ConnectionManager()
        a, b = LiveSocket(), LiveSocket()
        await m.connect(a)
        await m.connect(b)
        await m.close_all()
        assert len(m) == 0
        assert a.closed and b.closed
