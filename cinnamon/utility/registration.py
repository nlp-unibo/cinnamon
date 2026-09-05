from __future__ import annotations

import ast
import importlib
import types
from enum import Enum
from importlib.machinery import PathFinder
from pathlib import Path
from typing import AbstractSet, Any, List, Optional, Tuple, Union

__all__ = [
    "NamespaceExtractor",
    "Tags",
    "TAGGABLE_TYPES",
    "match_name",
    "match_namespace",
    "match_tags",
    "import_class_from_string",
    "locate_module",
]


# An AbstractSet so that both set and frozenset satisfy it: RegistrationKey
# normalises its tags to a frozenset, which is not a Set[str].
Tags = Optional[AbstractSet[str]]

TAGGABLE_TYPES = [str, int, float, bool, types.NoneType, Enum]


class NamespaceExtractor(ast.NodeVisitor):
    """
    Finds the namespaces a configuration module registers into, without running it.

    ``Registry.build`` needs to know which namespaces live in which directory
    before it imports anything, so this reads the decorators and registration
    calls straight from the AST.

    A namespace is discovered when it is a literal, or a module-level constant
    bound to one -- ``NAMESPACE = "myproject"`` at the top of the file is the
    common idiom and resolves fine. Anything computed at runtime cannot be read
    without executing the module, and is skipped rather than guessed at: the
    previous implementation took the text after ``namespace=`` and would record
    the string ``"NAMESPACE"`` as though it were a real namespace.
    """

    REGISTER_DECORATOR = "register"
    REGISTER_METHOD_DECORATOR = "register_method"
    REGISTRATION_CALLS = frozenset({"register_configuration"})

    def __init__(self):
        self.namespaces: List[str] = []
        self.register_flag = False
        self._constants: dict = {}

    def process(self, filename: Path) -> List[str]:
        # Reset: one extractor instance is reused for every file in a build, and
        # a flag left set by one module used to leak into the next.
        self.register_flag = False
        self.namespaces = []
        self._constants = {}

        with filename.open("r") as f:
            tree = ast.parse(f.read(), filename)

        self._collect_constants(tree)
        self.visit(tree)

        namespaces = list(self.namespaces)
        self.namespaces.clear()
        return namespaces

    def _collect_constants(self, tree: ast.Module) -> None:
        """Record module-level ``NAME = "literal"`` bindings."""
        for node in tree.body:
            targets = []
            if isinstance(node, ast.Assign):
                targets = node.targets
            elif isinstance(node, ast.AnnAssign):
                targets = [node.target]

            value = getattr(node, "value", None)
            if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
                continue
            for target in targets:
                if isinstance(target, ast.Name):
                    self._constants[target.id] = value.value

    @staticmethod
    def _called_name(node: ast.AST) -> Optional[str]:
        """The bare name of what a decorator or call refers to."""
        target = node.func if isinstance(node, ast.Call) else node
        if isinstance(target, ast.Name):
            return target.id
        if isinstance(target, ast.Attribute):
            return target.attr
        return None

    def _literal_keyword(self, node: ast.Call, name: str) -> Optional[str]:
        """A keyword argument's value, if it is a string we can read statically."""
        for keyword in node.keywords:
            if keyword.arg != name:
                continue
            if isinstance(keyword.value, ast.Constant):
                value = keyword.value.value
                return value if isinstance(value, str) else None
            if isinstance(keyword.value, ast.Name):
                return self._constants.get(keyword.value.id)
        return None

    def visit_FunctionDef(self, node):
        # Saved and restored so the flag describes *this* function only, rather
        # than everything the visitor happens to reach afterwards.
        previous_flag = self.register_flag
        self.register_flag = False

        for decorator in node.decorator_list:
            name = self._called_name(decorator)

            if name == self.REGISTER_METHOD_DECORATOR and isinstance(
                decorator, ast.Call
            ):
                namespace = self._literal_keyword(decorator, "namespace")
                if namespace is not None:
                    self.namespaces.append(namespace)
                break

            if name == self.REGISTER_DECORATOR:
                self.register_flag = True
                break

        self.generic_visit(node)
        self.register_flag = previous_flag

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Call(self, node):
        # Only registration calls carry a namespace. Reading every call with
        # keywords meant a Param(description=...) inside a @register function
        # raised IndexError on the missing namespace.
        if self.register_flag and self._called_name(node) in self.REGISTRATION_CALLS:
            namespace = self._literal_keyword(node, "namespace")
            if namespace is not None:
                self.namespaces.append(namespace)
        self.generic_visit(node)


def match_name(name: str, names: Optional[Union[List[str], str]] = None):
    if names is None:
        return True

    names = names if isinstance(names, list) else [names]

    return name in names


def match_namespace(namespace: str, namespaces: Optional[Union[List[str], str]] = None):
    if namespaces is None:
        return True

    namespaces = namespaces if isinstance(namespaces, list) else [namespaces]

    return namespace in namespaces


def match_tags(a_tags: AbstractSet[str], b_tags: Tags) -> bool:
    if b_tags is None:
        return True

    if not len(a_tags) and None in b_tags:
        return True

    if len(a_tags) and None in b_tags:
        b_tags = b_tags - {None}

    if not len(b_tags - a_tags):
        return True

    return False


def import_class_from_string(path: str) -> type:
    """
    Import the class named by a dotted *path*.

    The split between module and attribute is found by trying the longest
    importable prefix, rather than assuming the last segment is the class.
    A nested class -- ``pkg.module.Outer.Inner`` -- has two attribute segments,
    and splitting once would try to import ``pkg.module.Outer``.
    """
    segments = path.split(".")
    for split in range(len(segments) - 1, 0, -1):
        module_path = ".".join(segments[:split])
        try:
            target: Any = importlib.import_module(module_path)
        except ImportError:
            continue
        for attribute in segments[split:]:
            target = getattr(target, attribute)
        return target

    # Nothing was importable: re-raise the failure for the natural split, whose
    # message names the module the caller most likely meant.
    return getattr(importlib.import_module(".".join(segments[:-1])), segments[-1])


def locate_module(module_path: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Find a module's source file **without importing anything**.

    Returns ``(origin, missing_segment)``: the file backing *module_path*, and
    the first dotted segment that could not be found.

    **Presence is signalled by** ``missing_segment is None``, not by ``origin``.
    A namespace package -- a directory with no ``__init__.py`` -- resolves
    successfully and yet has no file of its own, so it comes back as
    ``(None, None)``.

    ``importlib.util.find_spec`` cannot be used for this. Resolving a dotted
    path there imports the parent packages to read their ``__path__`` -- for
    ``sklearn.svm`` that costs 619 ms against 0.11 ms here, near enough the full
    import it was meant to avoid. Walking segment by segment and threading each
    package's ``submodule_search_locations`` into the next lookup keeps
    ``PathFinder`` on the filesystem, where it never executes module code.
    """
    search: Optional[List[str]] = None
    origin: Optional[str] = None

    for index, segment in enumerate(module_path.split(".")):
        try:
            spec = PathFinder.find_spec(segment, search)
        except (ImportError, ValueError):  # pragma: no cover - odd path entries
            spec = None

        if spec is None:
            return None, ".".join(module_path.split(".")[: index + 1])

        origin = spec.origin
        if spec.submodule_search_locations is None:
            # A plain module: nothing further can be nested inside it.
            search = None
        else:
            search = list(spec.submodule_search_locations)

    return origin, None
