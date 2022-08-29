from dataclasses import dataclass
from typing import Set


@dataclass(eq=True, frozen=True)
class Node:
    name: str
    text: str

    def as_dot(self) -> str:
        return f'{self.name} [label="{self.text}"];'


@dataclass(eq=True, frozen=True)
class Edge:
    tail: str
    head: str

    def as_dot(self) -> str:
        return f"{self.tail} -> {self.head}"


@dataclass(eq=True, frozen=True)
class Graph:
    nodes: Set[Node]
    edges: Set[Edge]

    def as_dot(self) -> str:
        lines = []
        lines.append(f"digraph {{")
        for node in self.nodes:
            lines.append(f"  {node.as_dot()}")
        for edge in self.edges:
            lines.append(f"  {edge.as_dot()}")
        lines.append(f"}}")
        return "\n".join(lines)

    def without_unconnected_nodes(self):
        connected_node_head_names = set(edge.head for edge in self.edges)
        connected_node_tail_names = set(edge.tail for edge in self.edges)
        connected_node_names = connected_node_head_names | connected_node_tail_names
        nodes = set(node for node in self.nodes if node.name in connected_node_names)
        return Graph(nodes=nodes, edges=self.edges)
