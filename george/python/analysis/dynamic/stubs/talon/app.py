from sys import platform as platform_name

from george.python.analysis.dynamic import (
    register as register,
    unregister as unregister,
)


platform = {
    "linux": "linux",
    "darwin": "mac",
    "win32": "windows",
}[platform_name]
