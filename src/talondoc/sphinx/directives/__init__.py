from collections.abc import Callable
from typing import TYPE_CHECKING, Any, cast

import sphinx.directives

if TYPE_CHECKING:
    from ..domains import TalonDomain
else:
    TalonDomain = Any


class TalonDocDirective(sphinx.directives.SphinxDirective):  # type: ignore[misc, name-defined]
    @property
    def talon(self) -> TalonDomain:
        return cast(TalonDomain, self.env.get_domain("talon"))

    @property
    def docstring_hook(self) -> Callable[[str, str], str | None]:
        docstring_hook = self.env.config["talon_docstring_hook"]

        match docstring_hook:
            case None:

                def __docstring_hook(sort: str, name: str) -> str | None:
                    return None
            case dict():

                def __docstring_hook(sort: str, name: str) -> str | None:
                    value = docstring_hook.get(sort, {}).get(name, None)
                    if not (value is None or isinstance(value, str)):
                        raise ValueError(
                            f"value must be a string or None and is ${value!r}"
                        )
                    return value
            case _:

                def __docstring_hook(sort: str, name: str) -> str | None:
                    value = docstring_hook(sort, name)
                    if not (value is None or isinstance(value, str)):
                        raise ValueError(
                            f"value must be a string or None and is ${value!r}"
                        )
                    return value

        return __docstring_hook


class TalonDocObjectDescription(
    sphinx.directives.ObjectDescription[str],  # type: ignore[misc]
    TalonDocDirective,
):
    pass
