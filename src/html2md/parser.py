"""``IncrementalDriver`` — wraps lxml's target parser and drives the feed loop.

The driver constructs ``etree.HTMLParser(target=MarkdownEmitter, recover=True,
huge_tree=True)`` and feeds bytes in bounded chunks. The target parser invokes the
emitter's SAX callbacks *inside* ``feed()`` (no DOM is built — O(depth) memory), and
``parser.close()`` returns the emitter's ``close()`` result (the Markdown string).

* ``recover=True`` — parse malformed HTML the way a browser would.
* ``huge_tree=True`` — **mandatory**: without it libxml2 silently truncates large
  documents (confirmed by the GIL/parse spike). Set unconditionally.

It is a context manager: ``close()`` always runs (even on exception) to flush trailing
output and release the C parser, so a conversion that raises mid-feed leaks nothing.
"""

from __future__ import annotations

import logging
from types import TracebackType

from lxml import etree

from .emitter import MarkdownEmitter
from .options import Options

logger = logging.getLogger("html2md")


class IncrementalDriver:
    """Feeds bytes into a target-parser + Markdown emitter and yields the result."""

    __slots__ = ("options", "emitter", "_parser", "_closed", "_result")

    def __init__(self, options: Options | None = None) -> None:
        self.options = options or Options()
        self.emitter = MarkdownEmitter(self.options)
        # encoding pins libxml2's decode: a charset-less fragment would otherwise
        # default to ISO-8859-1 and mojibake UTF-8 input (e.g. "Café" → "CafÃ©"). A
        # document with its own <meta charset>/BOM still overrides this.
        self._parser = etree.HTMLParser(
            target=self.emitter,
            recover=True,
            huge_tree=True,
            encoding=self.options.default_encoding,
        )
        self._closed = False
        self._result: str | None = None

    def feed(self, data: bytes) -> None:
        """Feed one chunk of bytes. Callbacks fire (and emit) inside this call."""
        if self._closed:
            raise RuntimeError("IncrementalDriver.feed after close()")
        self._parser.feed(data)

    def feed_all(self, data: bytes) -> None:
        """Feed an entire document in ``Options.chunk_size`` byte chunks."""
        step = self.options.chunk_size
        for start in range(0, len(data), step):
            self.feed(data[start:start + step])

    def drain(self) -> str:
        """Return Markdown safe to emit now (streaming), removing it from the emitter
        buffer. Empty until a top-level block completes. See ``MarkdownEmitter.drain``."""
        if self._closed:
            return ""
        return self.emitter.drain()

    def close(self) -> str:
        """Finalize the parse, flush trailing Markdown, release the C parser, and
        return the document. Idempotent."""
        if self._closed:
            assert self._result is not None
            return self._result
        try:
            self._result = self._parser.close()
        except etree.XMLSyntaxError:
            # Empty / element-free input: lxml raises "no element found" instead of
            # invoking the target's close(). There is nothing to convert — return the
            # emitter's (empty) output. recover=True handles genuinely malformed input
            # without raising here.
            self._result = self.emitter.close()
        finally:
            self._closed = True
            self._log_recovery()
        return self._result

    def _log_recovery(self) -> None:
        error_log = getattr(self._parser, "error_log", None)
        if error_log:
            logger.warning("html2md recovered from %d HTML parse issue(s)", len(error_log))

    def __enter__(self) -> IncrementalDriver:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        # Always release the C parser. If we're already unwinding an exception, don't
        # mask it with a secondary error from close().
        try:
            self.close()
        except Exception:
            if exc_type is None:
                raise
            logger.debug("suppressed error closing driver during exception unwind",
                         exc_info=True)
