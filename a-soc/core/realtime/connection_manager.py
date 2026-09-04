"""
core/realtime/connection_manager.py
Fan-out to connected WebSocket clients.

The previous implementation lived in api.py and had two defects:

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

1. A single dead client aborted the whole loop, so every client after it in the
   list received nothing. The dead socket was never removed, so it poisoned
   every subsequent broadcast too.

   This was not merely a dropped message. ``background_telemetry()`` calls
   ``broadcast`` inside ``while True`` with no exception handling, so the first
   raised error killed that task permanently -- the live telemetry feed stopped
   for every client, for the lifetime of the process, the first time anyone
   closed a browser tab.

2. ``disconnect()`` used ``list.remove()``, which raises ``ValueError`` when the
   socket is not registered. A client that errored during ``connect`` and then
   disconnected took the handler down with it.

Both are covered by tests in tests/unit/test_connection_manager.py.
"""

from __future__ import annotations

import asyncio
import contextlib
from typing import Any, Protocol

from core.logging_config import get_logger

logger = get_logger(__name__)


class SupportsSendJson(Protocol):
    """The slice of WebSocket this class uses. Keeps tests free of a real socket."""

    async def send_json(self, data: Any) -> None: ...


class ConnectionManager:
    """Tracks live WebSocket clients and fans messages out to them."""

    def __init__(self, send_timeout: float = 5.0) -> None:
        self._connections: list[SupportsSendJson] = []
        self._lock = asyncio.Lock()
        self.send_timeout = send_timeout

    # ``api.py`` and existing tests reach for this name.
    @property
    def active_connections(self) -> list[SupportsSendJson]:
        return self._connections

    @active_connections.setter
    def active_connections(self, value: list[SupportsSendJson]) -> None:
        self._connections = value

    def __len__(self) -> int:
        return len(self._connections)

    async def connect(self, websocket: Any) -> None:
        await websocket.accept()
        self._connections.append(websocket)
        logger.info("ws_connected", total=len(self._connections))

    def disconnect(self, websocket: Any) -> None:
        """Remove a client. Safe to call for a socket that was never added."""
        try:
            self._connections.remove(websocket)
        except ValueError:
            logger.debug("ws_disconnect_unknown_socket")
            return
        logger.info("ws_disconnected", total=len(self._connections))

    async def broadcast(self, message: dict) -> int:
        """
        Send to every client. Returns how many received it.

        A client that raises, times out, or has gone away is dropped; it never
        prevents delivery to the others, and never propagates to the caller.
        """
        targets = list(self._connections)
        if not targets:
            return 0

        results = await asyncio.gather(
            *(self._send_one(conn, message) for conn in targets),
            return_exceptions=True,
        )

        dead = [conn for conn, ok in zip(targets, results, strict=True) if ok is not True]
        if dead:
            for conn in dead:
                self.disconnect(conn)
            logger.warning(
                "ws_pruned_dead_clients", pruned=len(dead), remaining=len(self._connections)
            )

        return len(targets) - len(dead)

    async def _send_one(self, conn: SupportsSendJson, message: dict) -> bool:
        try:
            await asyncio.wait_for(conn.send_json(message), timeout=self.send_timeout)
        except (TimeoutError, asyncio.CancelledError):
            logger.warning("ws_send_timeout")
            return False
        except Exception as exc:  # a client going away must not break the fan-out
            logger.warning("ws_send_failed", error=str(exc))
            return False
        return True

    async def close_all(self) -> None:
        """Drop every client. Used on shutdown."""
        for conn in list(self._connections):
            with contextlib.suppress(Exception):
                close = getattr(conn, "close", None)
                if close is not None:
                    await close()
        self._connections.clear()
