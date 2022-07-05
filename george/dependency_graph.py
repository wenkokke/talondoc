from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import ast
import re
from typing import Any, Optional, Sequence, Set


DefType = Enum("DefType", ["Action", "List", "Capture"])

@dataclass
class DefInfo:
    name: str
    scope: str
    is_override: bool
    has_default_value: bool
    def_type: DefType
    ast: Optional[Any] = None
    file: Optional[Path] = None
    baseurl: Optional[str] = None

    def __str__(self):
        return f"{self.scope}.{self.name}"

    def url(self) -> Optional[str]:
        if self.baseurl is None or self.file is None or self.ast is None:
            return None
        else:
            return (
                f"{self.baseurl}/{self.file}#L{self.ast.lineno}-L{self.ast.end_lineno}"
            )

    def anchor(self) -> Optional[str]:
        if not self.file is None:
            if not self.is_override:
                if self.scope == "user":
                    return DependencyGraph.escape_anchor(f"{self.file}_mod_def_{self}")
            else:
                return DependencyGraph.escape_anchor(f"{self.file}_ctx_def_{self}")
        return None


class DependencyGraph(ast.NodeVisitor):
    @staticmethod
    def escape_anchor(any: Any) -> str:
        text: str = any if type(any) == str else str(any)
        return "".join(c if c.isalnum() else "_" for c in text)

    @staticmethod
    def telescope(func: ast.Expr) -> Sequence[str]:
        if type(func) == ast.Name:
            return (func.id,)
        if type(func) == ast.Attribute:
            return (*DependencyGraph.telescope(func.value), func.attr)
        raise ValueError(func)

    @staticmethod
    def has_body(func: ast.FunctionDef):
        if len(func.body) == 1:
            stmt: ast.stmt = func.body[0]
            if type(stmt) == ast.Expr:
                if type(stmt.value) == ast.Constant:
                    if type(stmt.value.value) == str:
                        return True
        return False

    def guess_action_class_info(self, cls: ast.ClassDef):
        for decorator in cls.decorator_list:
            # mod.action_class
            try:
                if (
                    re.match("mod", decorator.value.id)
                    and decorator.attr == "action_class"
                ):
                    self._action_class_is_override = False
                    self._action_class_scope = "user"
                    return
            except AttributeError:
                pass
            # ctx.action_class(scope)
            try:
                if (
                    re.match("ctx", decorator.func.value.id)
                    and decorator.func.attr == "action_class"
                ):
                    self._action_class_is_override = True
                    self._action_class_scope = decorator.args[0].value
                    return
            except AttributeError:
                pass

    def __init__(self, baseurl: str):
        # constant
        self.baseurl: str = baseurl
        # set by self.open
        self.file: Optional[Path] = None
        # set by self.visit_ClassDef
        self._action_class_is_override: Optional[bool] = None
        self._action_class_scope: Optional[str] = None
        # set by self.visit_*
        self._def_list: list[DefInfo] = []
        self._use_list: list[str] = []
        # only ever added to
        self._file_to_defs: dict[str, Sequence[DefInfo]] = {}
        self._file_to_uses: dict[str, Sequence[str]] = {}
        self._name_to_mod_def_info: dict[str, DefInfo] = {}
        self._name_to_ctx_def_infos: dict[str, Sequence[DefInfo]] = {}

    def files(self):
        return self._file_to_defs.keys()

    def def_infos(self, file: str) -> Sequence[DefInfo]:
        return self._file_to_defs.get(file, ())

    def uses(self, file: str) -> Sequence[str]:
        return self._file_to_uses.get(file, ())

    def get_ctx_def_infos(self, any: Any) -> Sequence[DefInfo]:
        name: str = any if type(any) == str else str(any)
        return tuple(self._name_to_ctx_def_infos.get(name, []))

    def get_mod_def_info(self, any: Any) -> DefInfo:
        name: str = any if type(any) == str else str(any)
        top_level: str = name.split(".")[0]
        if top_level == "user":
            return self._name_to_mod_def_info.get(name)
        else:
            return DefInfo(
                name=name,
                scope=top_level,
                is_override=False,
                has_default_value=False,
                def_type=DefType.Action,
            )

    def reset(self):
        self.file = None
        self._action_class_is_override = None
        self._action_class_scope = None
        self._def_list.clear()
        self._use_list.clear()

    @contextmanager
    def open(self, file: Path):
        self.file = file
        yield
        self._file_to_defs[str(file)] = tuple(self._def_list)
        self._file_to_uses[str(file)] = tuple(self._use_list)
        self.reset()

    def process_python(self, file: Path):
        with file.open("r") as f:
            tree = ast.parse(f.read(), filename=str(file))
        with self.open(file):
            self.visit(tree)

    ACTION_NAME_PATTERN = re.compile(
        r"(?P<action_name>(([a-z][A-Za-z0-9]*)\.)+([a-z][A-Za-z0-9]*))\([^\)]*\)"
    )
    LIST_NAME_PATTERN = re.compile(
        r"(?P<list_name>\{(([a-z][A-Za-z0-9]*)\.)+([a-z][A-Za-z0-9]*))\}"
    )
    CAPTURE_NAME_PATTERN = re.compile(
        r"(?P<capture_name><(([a-z][A-Za-z0-9]*)\.)+([a-z][A-Za-z0-9]*))>"
    )

    def process_talon(self, file: Path):
        with self.open(file):
            with file.open("r") as f:
                talon_script = f.read()
            for match in DependencyGraph.ACTION_NAME_PATTERN.finditer(talon_script):
                self._use_list.append(match.group("action_name"))
            for match in DependencyGraph.LIST_NAME_PATTERN.finditer(talon_script):
                self._use_list.append(match.group("list_name"))
            for match in DependencyGraph.CAPTURE_NAME_PATTERN.finditer(talon_script):
                self._use_list.append(match.group("capture_name"))

    def process(self, *paths: Path):
        for file in paths:
            if file.match("**.py"):
                self.process_python(file)
            if file.match("**.talon"):
                self.process_talon(file)

    def visit_Call(self, call: ast.Call):
        try:
            telescope = DependencyGraph.telescope(call.func)
            # use action
            if telescope[0] == "actions":
                action_name = ".".join(telescope[1:])
                self._use_list.append(action_name)
            # define list
            if re.match("mod", telescope[0]) and telescope[1] == "list":
                list_name = call.args[0].value
                self._def_list.append(
                    DefInfo(
                        name=list_name,
                        scope=list_name.split(".")[0],
                        is_override=False,
                        has_default_value=False,
                        def_type=DefType.List,
                    )
                )
        except ValueError:
            pass
        self.generic_visit(call)

    def visit_ClassDef(self, cls: ast.ClassDef):
        self.action_class_info = self.guess_action_class_info(cls)
        self.generic_visit(cls)
        self.action_class_info = None

    def visit_FunctionDef(self, func: ast.FunctionDef):
        if self.action_class_info:
            action = DefInfo(
                name=func.name,
                scope=self._action_class_scope,
                is_override=self._action_class_is_override,
                def_type=DefType.Action,
                ast=func,
                file=self.file,
                baseurl=self.baseurl,
            )
            action_name = str(action)
            self._def_list.append(action)
            if action.is_override:
                if not action_name in self._name_to_ctx_def_infos:
                    self._name_to_ctx_def_infos[action_name] = []
                self._name_to_ctx_def_infos[action_name].append(action)
            else:
                self._name_to_mod_def_info[action_name] = action
        self.generic_visit(func)

    def usage_graph(self, unconnected_nodes: bool = True) -> Graph:
        nodes = []
        edges = []
        for file in self.files():
            nodes.append(Node(anchor=DependencyGraph.escape_anchor(file), label=file))
            for name in self.uses(file):
                mod_def_info = self.get_mod_def_info(name)
                if mod_def_info:
                    head = DependencyGraph.escape_anchor(file)
                    tail = DependencyGraph.escape_anchor(mod_def_info.file)
                    edges.append(Edge(head, tail))
        nodes = set(nodes)
        edges = set(edges)
        graph = Graph(nodes=set(nodes), edges=set(edges))
        return graph if unconnected_nodes else graph.without_unconnected_nodes()

    def context_graph(self, unconnected_nodes: bool = True) -> Graph:
        nodes = []
        edges = []
        for file in self.files():
            def_infos = self.def_infos(file)
            nodes.append(Node(anchor=DependencyGraph.escape_anchor(file), label=file))
            for def_info in def_infos:
                if def_info.is_override:
                    mod_def_info = self.get_mod_def_info(def_info)
                    if mod_def_info:
                        head = DependencyGraph.escape_anchor(mod_def_info.file)
                        tail = DependencyGraph.escape_anchor(def_info.file)
                        edges.append(Edge(head, tail))
        nodes = set(nodes)
        edges = set(edges)
        graph = Graph(nodes=set(nodes), edges=set(edges))
        return graph if unconnected_nodes else graph.without_unconnected_nodes()

    def context_html(self):
        lines = []
        for file in self.files():
            def_infos = self.def_infos(file)
            if def_infos:
                lines.append(f'<h1 id="{file}">File <tt>{file}</tt></h1>')
                lines.append(f"<ul>")
                for def_info in sorted(def_infos, key=str):
                    lines.append(f"<li>")
                    if not (def_info.is_override):
                        lines.append(f'<a id="{def_info.anchor()}">')
                        lines.append(f"Defines <tt>{def_info}</tt>")
                        lines.append(f'(<a href="{def_info.url()}">Source</a>)')
                        lines.append(f"</a>")
                        lines.append(f"<br />")
                        if not def_info.ast is None:
                            lines.append(f'<p class="doc_string">')
                            doc_string = (
                                ast.get_docstring(def_info.ast)
                                .splitlines()[0]
                                .strip()
                                .rstrip(".")
                            )
                            lines.append(f"<i>{doc_string}.</i>")
                            lines.append(f"</p>")
                        if not def_info.is_override:
                            action_refine_infos = self.get_ctx_def_infos(str(def_info))
                            if action_refine_infos:
                                lines.append(f"<p>")
                                lines.append("Refined in:")
                                lines.append(f"<ul>")
                                for action_refine_info in action_refine_infos:
                                    lines.append(f"<li>")
                                    href = f"#{action_refine_info.anchor()}"
                                    lines.append(f'<a href="{href}">')
                                    lines.append(f"<tt>{action_refine_info.file}</tt>")
                                    lines.append(f"</a>")
                                    lines.append(f"</li>")
                                lines.append(f"</ul>")
                                lines.append(f"</p>")
                    else:
                        action_define_info = self.get_mod_def_info(str(def_info))
                        lines.append(f'<a id="{def_info.anchor()}">')
                        action_name = f"<tt>{action_define_info}</tt>"
                        if action_define_info:
                            href = f"#{action_define_info.anchor()}"
                            lines.append(f'Refines <a href="{href}">{action_name}</a>')
                        else:
                            lines.append(f"Refines {action_name}")
                        lines.append(f'(<a href="{def_info.url()}">Source</a>)')
                        lines.append(f"</a>")
                    lines.append(f"</li>")
                lines.append(f"</ul>")
        return "\n".join(lines)


dg = DependencyGraph(baseurl="https://github.com/knausj85/knausj_talon/blob/main")
dg.process(*Path(".").glob("**/*.py"), *Path(".").glob("**/*.talon"))

with open("actions.md", "w") as f:
    f.write(dg.context_html())

with open("context_graph.dot", "w") as f:
    f.write(dg.context_graph(unconnected_nodes=False).as_dot())

with open("usage_graph.dot", "w") as f:
    f.write(dg.usage_graph(unconnected_nodes=False).as_dot())
