import ast
from copy import deepcopy
from pathlib import Path
from typing import List
import functools
import inspect

__all__ = [
    'NamespaceExtractor',
    'get_method_class'
]


class NamespaceExtractor(ast.NodeVisitor):

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
            if parsed_item.startswith('register_config('):
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


def get_method_class(meth):
    if isinstance(meth, functools.partial):
        return get_method_class(meth.func)
    if inspect.ismethod(meth) or \
            (inspect.isbuiltin(meth)
             and getattr(meth, '__self__', None) is not None
             and getattr(meth.__self__, '__class__', None)):
        for cls in inspect.getmro(meth.__self__.__class__):
            if meth.__name__ in cls.__dict__:
                return cls
        meth = getattr(meth, '__func__', meth)  # fallback to __qualname__ parsing
    if inspect.isfunction(meth):
        cls = getattr(inspect.getmodule(meth),
                      meth.__qualname__.split('.<locals>', 1)[0].rsplit('.', 1)[0],
                      None)
        if isinstance(cls, type):
            return cls
    return getattr(meth, '__objclass__', None)
