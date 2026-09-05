from __future__ import annotations

import ast
import importlib
import types
from copy import deepcopy
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
    Static code analyzer that parses cinnamon-compliant scripts for registrations.
    """

    def __init__(self):
        self.namespaces = []
        self.register_flag = False

    def process(self, filename: Path) -> List[str]:
        with filename.open("r") as f:
            tree = ast.parse(f.read(), filename)
            self.visit(tree)
        namespaces = deepcopy(self.namespaces)
        self.namespaces.clear()
        return namespaces

    def visit_FunctionDef(self, node):
        self.register_flag = False
        for item in node.decorator_list:
            parsed_item = ast.unparse(item)

            # For register_config only
            if parsed_item.startswith("register_method("):
                keywords = [ast.unparse(item) for item in item.keywords]
                namespace = (
                    [item for item in keywords if item.startswith("namespace")][0]
                    .split("namespace=")[-1]
                    .strip()
                )
                namespace = namespace.replace("'", "").replace('"', "")
                self.namespaces.append(namespace)
                break

            # For register only
            if parsed_item.startswith("register"):
                self.register_flag = True
                break

        self.generic_visit(node)

    def visit_Call(self, node):
        if self.register_flag:
            call_args = [ast.unparse(keyword) for keyword in node.keywords]
            if len(call_args):
                namespace = (
                    [item for item in call_args if item.startswith("namespace")][0]
                    .split("namespace=")[-1]
                    .strip()
                )
                namespace = namespace.replace("'", "").replace('"', "")
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
