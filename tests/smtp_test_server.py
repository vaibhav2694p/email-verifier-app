import asyncio
import logging
import re
import threading
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

SMTP_220 = b"220 Test SMTP Server Ready"
SMTP_250 = b"250 OK"
SMTP_550 = b"550 User unknown"
SMTP_450 = b"450 Try again later"
SMTP_451 = b"451 Try again later"
SMTP_530 = b"530 Authentication required"
SMTP_221 = b"221 Bye"
SMTP_500 = b"500 Command not recognized"

DEFAULT_RESPONSE_MAP: Dict[str, bytes] = {
    "accepted@example.test": SMTP_250,
    "rejected@example.test": SMTP_550,
    "unknown@example.test": SMTP_550,
    "temporary@example.test": SMTP_451,
    "greylisted@example.test": SMTP_450,
    "catchall@example.test": SMTP_250,
    "timeout@example.test": SMTP_250,
    "tlsrequired@example.test": SMTP_530,
}

_TIMEOUT_DELAY = 2.0
_CRLF = b"\r\n"
_END_MARKER = re.compile(rb"^(EHLO|HELO|MAIL\s+FROM|RCPT\s+TO|QUIT|NOOP|RSET|DATA)\b", re.IGNORECASE)


class _SmtpProtocol(asyncio.Protocol):
    def __init__(self, response_map: Dict[str, bytes]) -> None:
        self._response_map = response_map
        self._transport: Optional[asyncio.Transport] = None
        self._buffer = b""

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        self._transport = transport  # type: ignore[assignment]
        logger.debug("Connection from %s", transport.get_extra_info("peername"))
        self._send(SMTP_220)

    def connection_lost(self, exc: Optional[Exception]) -> None:
        logger.debug("Connection closed")

    def data_received(self, data: bytes) -> None:
        self._buffer += data
        while _CRLF in self._buffer:
            line, self._buffer = self._buffer.split(_CRLF, 1)
            self._process_line(line.strip())

    def _send(self, response: bytes) -> None:
        if self._transport is not None:
            self._transport.write(response + _CRLF)

    def _process_line(self, line: bytes) -> None:
        logger.debug("Received: %s", line)
        upper = line.upper()

        if upper.startswith(b"QUIT"):
            self._send(SMTP_221)
            if self._transport is not None:
                self._transport.close()
            return

        if upper.startswith(b"NOOP"):
            self._send(SMTP_250)
            return

        if upper.startswith(b"RSET"):
            self._send(SMTP_250)
            return

        if upper.startswith(b"EHLO") or upper.startswith(b"HELO"):
            self._send(SMTP_250)
            return

        if upper.startswith(b"MAIL"):
            self._send(SMTP_250)
            return

        if upper.startswith(b"RCPT"):
            rcpt_match = re.search(rb"TO:\s*<([^>]+)>", line, re.IGNORECASE)
            if not rcpt_match:
                self._send(SMTP_500)
                return

            recipient = rcpt_match.group(1).decode("utf-8", errors="replace").lower().strip()
            response = self._response_map.get(recipient, SMTP_550)

            if recipient == "timeout@example.test":
                asyncio.get_event_loop().call_later(_TIMEOUT_DELAY, self._close_transport)
                return

            self._send(response)
            return

        if upper.startswith(b"DATA"):
            self._send(b"354 Go ahead")
            self._send(SMTP_250)
            return

        self._send(SMTP_500)

    def _close_transport(self) -> None:
        if self._transport is not None:
            try:
                self._transport.close()
            except Exception:
                pass


class TestSmtpServer:
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 1025,
        response_map: Optional[Dict[str, bytes]] = None,
    ) -> None:
        self._host = host
        self._port = port
        self._response_map = dict(response_map) if response_map else dict(DEFAULT_RESPONSE_MAP)
        self._server: Optional[asyncio.AbstractServer] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._started_event = threading.Event()
        self._stopped_event = threading.Event()
        self._stopped_event.set()

    def _create_protocol(self) -> _SmtpProtocol:
        return _SmtpProtocol(self._response_map)

    async def _start_server(self) -> None:
        self._loop = asyncio.get_running_loop()
        self._server = await self._loop.create_server(
            self._create_protocol,
            self._host,
            self._port,
            reuse_address=True,
        )
        logger.info("Test SMTP server listening on %s:%d", self._host, self._port)
        self._started_event.set()
        await self._stopped_event.wait()
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
        logger.info("Test SMTP server stopped")

    def _run_loop(self) -> None:
        asyncio.set_event_loop(asyncio.new_event_loop())
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self._start_server())
        loop.close()

    def start(self) -> None:
        """Start the server in the current thread (blocking)."""
        self._stopped_event.clear()
        self._started_event.clear()
        self._run_loop()

    def stop(self) -> None:
        """Stop the server."""
        if self._loop is not None and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._stopped_event.set)
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=5)
        self._thread = None
        self._loop = None

    def run_in_thread(self) -> threading.Thread:
        """Start the server in a background thread."""
        self._stopped_event.clear()
        self._started_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="test-smtp-server")
        self._thread.start()
        return self._thread

    def wait_until_ready(self, timeout: float = 5) -> bool:
        """Block until the server is accepting connections."""
        return self._started_event.wait(timeout=timeout)

    @property
    def host(self) -> str:
        return self._host

    @property
    def port(self) -> int:
        return self._port

    @property
    def address(self) -> Tuple[str, int]:
        return (self._host, self._port)
