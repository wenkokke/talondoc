from dataclasses import dataclass
from logging import warn
from pathlib import Path
import re
from typing import Optional, Sequence
import ast

from george.types import *


def VariableTalonName(path: Path, node: ast.AST):
    warn(
        f"""
        Variable name in {path}:{node.lineno}-{node.end_lineno}:
        {ast.unparse(node)}
        """
    )


class PythonStaticPackageAnalysis:
    def __init__(self, package_root: Path):
        self.package_root = package_root

    def process_file(file_path: Path, package_root: Path = Path(".")) -> PythonFileInfo:
        return PythonStaticFileAnalysis(file_path, package_root).process()

    def process(self) -> PythonPackageInfo:
        file_infos = {}
        for file_path in self.package_root.glob("**/*.py"):
            file_path = file_path.relative_to(self.package_root)
            file_info = PythonStaticFileAnalysis(file_path, self.package_root).process()
            file_infos[str(file_path)] = file_info
        return PythonPackageInfo(
            file_infos=file_infos
        )


@dataclass
class QualifiedNameError(Exception):
    name: ast.expr


def qualified_name(name: ast.expr) -> Sequence[str]:
    if type(name) == ast.Name:
        return (name.id,)
    if type(name) == ast.Attribute:
        return (*qualified_name(name.value), name.attr)
    raise QualifiedNameError(name)


@dataclass
class DecoratorInfo:
    decorator_name: str
    decorator: ast.ClassDef
    scope: str
    matches: TalonMatches

    @staticmethod
    def from_ast(decorator_name: str, decorator: ast.expr) -> Optional["DecoratorInfo"]:
        # For @mod.action_class
        try:
            if re.match("mod", decorator.value.id) and decorator.attr == decorator_name:
                return DecoratorInfo(
                    decorator_name=decorator_name,
                    decorator=decorator,
                    scope="user",
                    matches=TalonModule(),
                )
        except AttributeError:
            pass
        # For @ctx.action_class(scope)
        try:
            if (
                re.match("ctx", decorator.func.value.id)
                and decorator.func.attr == decorator_name
            ):
                return DecoratorInfo(
                    decorator_name=decorator_name,
                    decorator=decorator,
                    scope=decorator.args[0].value,
                    matches=TalonContext(),
                )
        except AttributeError:
            pass
        return None


@dataclass
class ActionClassInfo:
    scope: str
    matches: TalonMatches
    class_def: ast.ClassDef = None

    @staticmethod
    def from_ast(class_def: ast.ClassDef) -> Optional["ActionClassInfo"]:
        for decorator in class_def.decorator_list:
            decorator_info = DecoratorInfo.from_ast("action_class", decorator)
            if decorator_info:
                return ActionClassInfo(
                    scope=decorator_info.scope,
                    matches=decorator_info.matches,
                    class_def=class_def,
                )
        return None


class PythonStaticFileAnalysis(ast.NodeVisitor):
    def __init__(self, file_path: Path, package_root: Path = Path(".")):
        self.package_root: Path = package_root
        self.python_file_info = PythonFileInfo(
            file_path=str(file_path)
        )
        self.action_class: Optional[ActionClassInfo] = None

    @property
    def file_path(self) -> str:
        return self.python_file_info.file_path

    def process(self) -> PythonFileInfo:
        path = self.package_root / self.file_path
        with path.open("r") as f:
            tree = ast.parse(f.read(), filename=self.file_path)
        self.visit(tree)
        return self.python_file_info

    def visit_ClassDef(self, class_def: ast.ClassDef):
        self.action_class = ActionClassInfo.from_ast(class_def)
        self.generic_visit(class_def)
        self.action_class = None

    def visit_Call(self, call: ast.Call):
        try:
            func_name = qualified_name(call.func)

            # Use Action
            if func_name[0] == "actions":
                name = ".".join(func_name[1:])
                self.python_file_info.add_use(TalonSort.Action, name)

            mod_var, list_func = func_name

            # Declare List
            if re.match("mod", mod_var) and list_func == "list":
                name = call.args[0].value
                try:
                    desc = call.args[1].value
                except (IndexError, AttributeError):
                    desc = None
                self.python_file_info.add_declaration(
                    TalonListDecl(
                        name=name,
                        matches=TalonModule(),
                        desc=desc,
                        source=Source.from_ast(self.file_path, call),
                    )
                )

            # Declare Tag
            if re.match("mod", mod_var) and list_func == "tag":
                name = call.args[0].value
                try:
                    desc = call.args[1].value
                except (IndexError, AttributeError):
                    desc = None
                self.python_file_info.add_declaration(
                    TalonTagDecl(
                        name=name,
                        matches=TalonModule(),
                        desc=desc,
                        source=Source.from_ast(self.file_path, call),
                    )
                )
        except AttributeError:
            VariableTalonName(self.file_path, call)
        except (ValueError, IndexError, QualifiedNameError) as e:
            pass
        self.generic_visit(call)

    def visit_Subscript(self, subscript: ast.Subscript):
        try:
            ctx_var, list_func = qualified_name(subscript.value)

            # Override List
            if re.match("ctx", ctx_var) and list_func == "lists":
                name = subscript.slice.value
                self.python_file_info.add_declaration(
                    TalonListDecl(
                        name=name,
                        matches=TalonContext(),
                        source=Source.from_ast(self.file_path, subscript),
                    )
                )
        except (QualifiedNameError, ValueError, AttributeError):
            pass

    def visit_FunctionDef(self, function_def: ast.FunctionDef):
        if self.action_class:
            # Declare or Override Action
            name = f"{self.action_class.scope}.{function_def.name}"
            desc = ast.get_docstring(function_def)
            self.python_file_info.add_declaration(
                TalonActionDecl(
                    name=name,
                    matches=self.action_class.matches,
                    desc=desc,
                    source=Source.from_ast(self.file_path, function_def),
                )
            )
        else:
            for decorator in function_def.decorator_list:
                decorator_info = DecoratorInfo.from_ast("capture", decorator)
                if decorator_info:
                    # Declare or Override Capture
                    name = f"{decorator_info.scope}.{function_def.name}"
                    desc = ast.get_docstring(function_def)
                    self.python_file_info.add_declaration(
                        TalonCaptureDecl(
                            name=name,
                            matches=decorator_info.matches,
                            desc=desc,
                            source=Source.from_ast(self.file_path, function_def),
                        )
                    )
                    break
        self.generic_visit(function_def)
