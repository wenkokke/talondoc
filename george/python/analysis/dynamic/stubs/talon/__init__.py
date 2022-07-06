from .scripting.actions import Actions
from .scripting.scope import Scope
from .scripting.settings import Settings
from .scripting.registry import Registry
from .scripting.speech_system import SpeechSystem
from .scripting.module import Module as Module
from .scripting.context import Context as Context

actions: Actions = Actions()
scope: Scope = Scope()
settings: Settings = Settings()
registry: Registry = Registry()
speech_system: SpeechSystem = SpeechSystem()

