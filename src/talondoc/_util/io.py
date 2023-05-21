import io
import queue
import threading
from collections.abc import Callable, Iterator
from typing import Optional


class NonBlockingTextIOWrapper:
    _stream: io.TextIOWrapper
    _queue: queue.Queue[str]
    _daemon: threading.Thread

    def __init__(self, stream: io.TextIOWrapper, maxsize: int = 0) -> None:
        self._stream = stream
        self._queue = queue.Queue(maxsize=maxsize)
        self._daemon = threading.Thread(target=self._stream_reader, daemon=True)
        self._daemon.start()

    def _stream_reader(self) -> None:
        for line in self._stream:
            self._queue.put(line)
        self._stream.close()

    def readline(
        self, block: bool = False, timeout: Optional[float] = None
    ) -> Optional[str]:
        if self._queue.empty() and self._stream.closed:
            return None
        else:
            try:
                return self._queue.get(block=block, timeout=timeout)
            except queue.Empty:
                return None

    def readlines(
        self, minlines: int = 0, timeout: Optional[float] = None
    ) -> Iterator[str]:
        while True:
            line = self.readline(block=minlines > 0, timeout=timeout)
            minlines -= 1
            if line is None:
                return
            else:
                yield line

    def readuntil(
        self, predicate: Callable[[str], bool], timeout: Optional[float] = None
    ) -> Iterator[str]:
        yield from self.readwhile(
            predicate=lambda line: not predicate(line),
            timeout=timeout,
        )

    def readwhile(
        self, predicate: Callable[[str], bool], timeout: Optional[float] = None
    ) -> Iterator[str]:
        while True:
            line = self.readline(block=True, timeout=timeout)
            if line is not None:
                line = line.rstrip()
                if predicate(line):
                    yield line
                else:
                    break
            else:
                break
