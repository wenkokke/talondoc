from typing import TYPE_CHECKING, Any

from sphinx.directives import ObjectDescription

if TYPE_CHECKING:
    from talondoc.sphinx.domains import TalonDomain
else:
    TalonDomain = Any


class TalonListDirective(ObjectDescription):
    pass
