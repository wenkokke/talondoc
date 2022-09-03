import typing

import sphinx.directives

if typing.TYPE_CHECKING:
    from talondoc.sphinx.domains import TalonDomain
else:
    TalonDomain = typing.Any


class TalonDocDirective(sphinx.directives.SphinxDirective):
    @property
    def talon(self) -> TalonDomain:
        return typing.cast(TalonDomain, self.env.get_domain("talon"))


class TalonDocObjectDescription(sphinx.directives.ObjectDescription, TalonDocDirective):
    pass
