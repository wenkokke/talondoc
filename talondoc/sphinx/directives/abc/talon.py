import sphinx.directives
import typing


if typing.TYPE_CHECKING:
    from talondoc.sphinx.domains import TalonDomain
else:
    TalonDomain = typing.Any


class TalonDirective(sphinx.directives.SphinxDirective):
    @property
    def talon(self) -> TalonDomain:
        return typing.cast(TalonDomain, self.env.get_domain("talon"))


class TalonObjectDescription(sphinx.directives.ObjectDescription, TalonDirective):
    pass
