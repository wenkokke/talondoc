import george.python.analysis.dynamic as dynamic
import typing

def __getattr__(name: str) -> typing.Any:
    return dynamic.Stub()
