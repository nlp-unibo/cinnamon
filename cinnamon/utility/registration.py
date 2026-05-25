from __future__ import annotations
import os
import inspect

import ast
import types
from copy import deepcopy
from enum import Enum
from pathlib import Path
from typing import List, Optional, Set, Union

__all__ = [
    'NamespaceExtractor',
    'PythonSerializer',
    'Tags',
    'TAGGABLE_TYPES',
    'match_name',
    'match_namespace',
    'match_tags'
]

import cinnamon

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
            if len(call_args):
                namespace = [item for item in call_args if item.startswith('namespace')][0].split('namespace=')[-1].strip()
                namespace = namespace.replace('\'', '').replace("\"", '')
                self.namespaces.append(namespace)
        self.generic_visit(node)



class PythonSerializer:

    def __init__(
            self,
            filepath: Path,
            filename: str
    ):
        self.filepath = filepath
        self.filename = filename

        self.imports = [
            "from cinnamon.registry import register, Registry"
        ]
        self.configs = []
        self.key_to_function_mapping = {}
        self.config_counter = 1

    # TODO: check if we need to update sys.modules when importing external configurations
    # we can use external_namespaces from registry to check for this
    def serialize_configuration(
            self,
            config: "cinnamon.registry.Configuration",
            component_class: "cinnamon.registry.Component"
    ):
        serialization_string = [
            f"@register"
        ]

        function_name = f'register_configuration_{self.config_counter}'
        self.key_to_function_mapping[config.registration_key] = function_name
        serialization_string.append(f'def {function_name}():')

        config_module = inspect.getmodule(config.__class__)
        module_name = config_module.__name__
        class_name = config.__class__.__name__
        self.imports.append(f'from {module_name} import {class_name}')

        serialization_string.append(f'\tconfig = {class_name}()')
        for param_name, param in config.params.items():

            if isinstance(param.value, cinnamon.registry.RegistrationKey):
                param_value = f'{self.key_to_function_mapping[param.value]}()'
            else:
                # TODO: this does not work with custom classes
                # we cannot recover how it was instantiated unless we check the script line where it is defined
                value_module = inspect.getmodule(param.value.__class__)
                value_module_name = value_module.__name__

                param_value = repr(param.value)

                # TODO: we could import value_module_name and then use value_module_name.param_constructor_name to avoid conflicts
                if value_module_name != 'builtins':
                    param_constructor_name = param_value.split('(')[0]
                    self.imports.append(f'from {value_module_name.split(".")[0]} import {param_constructor_name}')

            serialization_string.append(
                f'\tconfig.add(name={repr(param_name)}, value={param_value}, description={param.description})'
            )

        component_module = inspect.getmodule(component_class)
        component_module_name = component_module.__name__
        self.imports.append(f'from {component_module_name} import {component_class.__name__}')

        serialization_string.append(
            f'{os.linesep}\tRegistry.register_configuration(config=config, '
            f'name={repr(config.registration_key.name)}, '
            f'tags={repr(config.registration_key.tags)}, '
            f'namespace={repr(config.registration_key.namespace)}, '
            f'component_class={component_class.__name__})'
        )

        self.config_counter += 1

        self.configs.append(os.linesep.join(serialization_string))

    def build_serialization_string(
            self
    ) -> str:
        return f"""
# Generated automatically

{os.linesep.join(self.imports)}

{os.linesep.join(self.configs)}
"""

    def serialize(
            self
    ):
        with self.filepath.joinpath(self.filename).open('w') as f:
            f.write(self.build_serialization_string())


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
