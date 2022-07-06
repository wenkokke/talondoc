from typing import IO
import io

def open(path: str, mode: str = 'rw') -> IO:
    return io.open(path, mode, encoding='utf-8')


def read(path: str, binary: bool = False):
    raise NotImplementedError()


def write(path: str, data: bytes, binary: bool = False):
    raise NotImplementedError()
