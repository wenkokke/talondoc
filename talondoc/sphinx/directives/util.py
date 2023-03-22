import re
from typing import Sequence, Union

from ...registry import Registry
from ...registry.entries.user import UserFileEntry, UserPackageEntry, UserTalonFileEntry


def find_package(registry: Registry, package_name: str) -> UserPackageEntry:
    candidate = registry.active_package_entry
    if candidate and (not package_name or candidate.get_namespace() == package_name):
        return candidate
    candidate = registry.packages.get(package_name, None)
    if candidate:
        return candidate
    raise ValueError(f"Could not find package '{package_name}'")


def resolve_packages(
    registry: Registry, packages: Sequence[Union[str, UserPackageEntry]]
) -> Sequence[UserPackageEntry]:
    buffer = []
    for package in packages:
        if isinstance(package, str):
            buffer.append(find_package(registry, package))
        else:
            buffer.append(package)
    if not buffer and registry.active_package_entry:
        buffer.append(registry.active_package_entry)
    return buffer


def find_file(
    registry: Registry,
    file_name: str,
    *,
    packages: Sequence[Union[str, UserPackageEntry]] = (),
) -> UserFileEntry:
    # Resolve any package names
    packages = resolve_packages(registry, packages)

    # Try lookup with '{file_name}' as name:
    result = registry.lookup("file", file_name)
    if result:
        return result

    # Try lookup with '{file_name}.talon' as name:
    result = registry.lookup("file", f"{file_name}.talon")
    if result:
        return result

    # Try searching in the package:
    for package in packages:
        for file in package.files:
            # Try comparison with '{file_name}' as path:
            if file_name == str(file.path):
                return file

            # Try comparison with '{file_name}.talon' as path:
            if isinstance(file, UserTalonFileEntry):
                if f"{file_name}.talon" == str(file.path):
                    return file

    raise ValueError(f"Could not find file '{file_name}'.")


def resolve_files(
    registry: Registry,
    files: Sequence[Union[str, UserFileEntry]],
    *,
    packages: Sequence[Union[str, UserPackageEntry]] = (),
) -> Sequence[UserFileEntry]:
    buffer = []
    for file in files:
        if isinstance(file, str):
            buffer.append(find_file(registry, file, packages=packages))
        else:
            buffer.append(file)
    return buffer


def wildcard_pattern(pattern: str) -> re.Pattern:
    """Compile a pattern with wildcards to a regular expression."""
    return re.compile(".*".join(map(re.escape, pattern.split("*"))))
