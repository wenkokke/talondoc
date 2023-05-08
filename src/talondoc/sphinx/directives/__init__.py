from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Optional, cast

import sphinx.directives

if TYPE_CHECKING:
    from talondoc.sphinx.domains import TalonDomain
else:
    TalonDomain = Any


class TalonDocDirective(sphinx.directives.SphinxDirective):
    @property
    def talon(self) -> TalonDomain:
        return cast(TalonDomain, self.env.get_domain("talon"))

    @property
    def docstring_hook(self) -> Callable[[str, str], Optional[str]]:
        docstring_hook = self.env.config["talon_docstring_hook"]
        if docstring_hook is None:

            def __docstring_hook(sort: str, name: str) -> Optional[str]:
                return None

            return __docstring_hook
        elif isinstance(docstring_hook, dict):

            def __docstring_hook(sort: str, name: str) -> Optional[str]:
                value = docstring_hook.get(sort, {}).get(name, None)
                assert value is None or isinstance(value, str)
                return value

            return __docstring_hook
        else:

            def __docstring_hook(sort: str, name: str) -> Optional[str]:
                value = docstring_hook(sort, name)
                assert value is None or isinstance(value, str)
                return value

            return __docstring_hook


class TalonDocObjectDescription(sphinx.directives.ObjectDescription, TalonDocDirective):
    pass
