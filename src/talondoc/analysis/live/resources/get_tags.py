import talon  # pyright: ignore[reportMissingImports]


def _get_tags() -> None:
    import json

    tag_dicts = []

    for mod in talon.registry.modules.values():
        for tag in mod._tags.values():
            tag_dicts.append(
                {
                    "name": tag.path,
                    "description": tag.desc,
                    "parent_name": mod.path,
                }
            )
    print(json.dumps(tag_dicts))


_get_tags()
del _get_tags
