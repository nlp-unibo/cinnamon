import ast
from typing import List
from copy import deepcopy
from pathlib import Path

__all__ = [
    'NamespaceExtractor'
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
        if 'register' in ast.unparse(node.decorator_list):
            self.register_flag = True
        else:
            self.register_flag = False

        self.generic_visit(node)

    def visit_Call(self, node):
        if self.register_flag:
            call_args = [ast.unparse(keyword) for keyword in node.keywords]
            namespace = [item for item in call_args if item.startswith('namespace')][0].split('namespace=')[-1].strip()
            namespace = namespace.replace('\'', '').replace("\"", '')
            self.namespaces.append(namespace)
        self.generic_visit(node)
