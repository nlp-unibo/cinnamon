from __future__ import annotations

import ast
import types
from copy import deepcopy
from enum import Enum
from pathlib import Path
from typing import List, Optional, Set, Union

__all__ = [
    'NamespaceExtractor',
    'Tags',
    'TAGGABLE_TYPES',
    'match_name',
    'match_namespace',
    'match_tags'
]

Tags = Optional[Set[str]]

TAGGABLE_TYPES = [
    str,
    int,
    float,
    bool,
    types.NoneType,
    Enum
]


class NamespaceExtractor(ast.NodeVisitor):
    """
    Static code analyzer that parses cinnamon-compliant scripts for registrations.
    """

    def __init__(
            self
    ):
        self.namespaces = []
        self.register_flag = False

    def process(
            self,
            filename: Path
    ) -> List[str]:
        with filename.open('r') as f:
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
            if parsed_item.startswith('register_method('):
                keywords = [ast.unparse(item) for item in item.keywords]
                namespace = [item for item in keywords if item.startswith('namespace')][0].split('namespace=')[
                    -1].strip()
                namespace = namespace.replace('\'', '').replace("\"", '')
                self.namespaces.append(namespace)
                break

            # For register only
            if parsed_item.startswith('register'):
                self.register_flag = True
                break

        self.generic_visit(node)

    def visit_Call(self, node):
        if self.register_flag:
            call_args = [ast.unparse(keyword) for keyword in node.keywords]
            namespace = [item for item in call_args if item.startswith('namespace')][0].split('namespace=')[-1].strip()
            namespace = namespace.replace('\'', '').replace("\"", '')
            self.namespaces.append(namespace)
        self.generic_visit(node)


def match_name(
        name: str,
        names: Optional[Union[List[str], str]] = None
):
    if names is None:
        return True

    names = names if type(names) == list else [names]

    return name in names


def match_namespace(
        namespace: str,
        namespaces: Optional[Union[List[str], str]] = None
):
    if namespaces is None:
        return True

    namespaces = namespaces if type(namespaces) == list else [namespaces]

    return namespace in namespaces


def match_tags(
        a_tags: "cinnamon.registry.Tags",
        b_tags: "cinnamon.registry.Tags"
):
    if b_tags is None:
        return True

    if not len(a_tags) and None in b_tags:
        return True

    if len(a_tags) and None in b_tags:
        b_tags.pop(None)

    if not len(b_tags.difference(a_tags)):
        return True

    return False
