from dataclasses import dataclass
from typing import Optional
from dataclasses_json import dataclass_json
from pathlib import Path
import json


@dataclass_json
@dataclass
class SimpleNodeType:
    type: str
    named: bool


@dataclass_json
@dataclass
class Field:
    multiple: bool
    required: bool
    types: list[SimpleNodeType]


@dataclass_json
@dataclass
class Children:
    multiple: bool
    required: bool
    types: list[SimpleNodeType]


@dataclass_json
@dataclass
class NodeType:
    type: str
    named: bool
    fields: Optional[dict[str, Field]] = None
    children: Optional[Children] = None


repository_path: Path = Path("vendor") / "tree-sitter-talon"
node_types_path: Path = repository_path / "src" / "node-types.json"

with node_types_path.open('r') as fp:
  node_types_body = fp.read()
node_types = NodeType.schema().loads(node_types_body, many=True)
print(node_types)
