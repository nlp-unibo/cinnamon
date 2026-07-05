from __future__ import annotations

import ast
import importlib.util
import json
import logging
import math
import sys
from dataclasses import dataclass
from logging import getLogger
from pathlib import Path
from typing import Any, AnyStr, Callable, Dict, List, Optional, Set, Tuple, Union

import networkx as nx
import pydantic
from pydantic import GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema

import cinnamon.component
import cinnamon.configuration
from cinnamon.utility.configuration import batched
from cinnamon.utility.exceptions import (
    AlreadyExpandedException,
    AlreadyRegisteredException,
    DisconnectedGraphException,
    InvalidDirectoryException,
    NamespaceNotFoundException,
    NotADAGException,
    NotBoundException,
    NotExpandedException,
    NotRegisteredException,
)
from cinnamon.utility.registration import (
    TAGGABLE_TYPES,
    NamespaceExtractor,
    Tags,
    import_class_from_string,
    match_name,
    match_namespace,
    match_tags,
)
from cinnamon.utility.sanity import time_it

logger = getLogger(__name__)

Constructor = Callable[[], "cinnamon.configuration.Configuration"]
Registration = Union["RegistrationKey", str]

__all__ = ["RegistrationKey", "register", "register_method", "Registry", "Registration"]


class RegistrationKey:
    """
    Compound key used for registration.
    """

    KEY_VALUE_SEPARATOR: str = "="
    ATTRIBUTE_SEPARATOR: str = "--"
    HIERARCHY_SEPARATOR: str = "."
    MAX_TAGS_PER_LINE: int = 6

    def __init__(
        self,
        name: str,
        namespace: Optional[str] = None,
        tags: Tags = None,
        description: Optional[str] = None,
        metadata: Optional[str] = None,
        special_tags: Tags = None,
        resolve_automatically: bool = True,
    ):
        """

        Args:
            name: A general identifier of the ``Configuration`` being registered.
            namespace: The namespace is a high-level identifier used to distinguish
            macro groups of registered Configuration. For example, a group of models
            may be implemented in Tensorflow and another one in Torch.
            You can distinguish between these two groups by specifying two distinct
            namespaces. Additionally, the namespace can also be used to
            distinguish among multiple users' registrations.
            In this case, the recommended naming convention is like the
            Huggingface's one: ``user/namespace``.
            tags: metadata for quick inspection of a registered ``Configuration``.
            In the case of ``Configuration`` with the same name and namespace
            (e.g., multiple models implemented by the same user), tags are used
            to distinguish among them.
            description: natural language description of a ``RegistrationKey``.
            metadata: optionally contains information about the invalidity of the
             ``RegistrationKey``
            special_tags: set of special tags for internal use.
        """
        self.name = name
        self.namespace = namespace if namespace is not None else "default"
        self.tags = tags if tags is not None else set()
        self.description = description
        self.metadata = metadata
        self.special_tags = special_tags if special_tags is not None else set()
        self.resolve_automatically = resolve_automatically

    # TODO: check other schema (e.g., string)
    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:

        # This tells Pydantic: "If the input is already a RegistrationKey, accept it."
        # You can chain this with other schemas if you want to allow users
        # to pass a dictionary that auto-converts to a RegistrationKey.
        return core_schema.is_instance_schema(cls)

    def __hash__(self) -> int:
        return hash(self.__str__())

    def __str__(self) -> str:
        to_return = [f"name{self.KEY_VALUE_SEPARATOR}{self.name}"]

        if self.tags is not None:
            tags = sorted(list(self.tags)) if self.tags else None
            if tags is not None:
                to_return.append(
                    f"{self.ATTRIBUTE_SEPARATOR}tags{self.KEY_VALUE_SEPARATOR}{tags}"
                )

        to_return.append(
            f"{self.ATTRIBUTE_SEPARATOR}namespace{self.KEY_VALUE_SEPARATOR}{self.namespace}"
        )
        return "".join(to_return)

    def __repr__(self) -> str:
        return (
            f"{RegistrationKey.__name__}(name={self.name}, namespace={self.namespace},"
            f" tags={self.tags}, description={self.description})"
        )

    def check_name(self, name: str):
        return self.name == name

    def check_tags(self, tags: Tags):
        if (self.tags is not None and tags is not None and self.tags == tags) or (
            self.tags is None and tags is None
        ):
            return True
        return False

    def check_namespace(self, namespace: str):
        if (
            self.namespace is not None
            and namespace is not None
            and self.namespace == namespace
        ) or (self.namespace is None and namespace is None):
            return True
        return False

    def __eq__(self, other) -> bool:
        if other is None or not isinstance(other, RegistrationKey):
            return False

        return (
            self.check_name(other.name)
            and self.check_tags(other.tags)
            and self.check_namespace(other.namespace)
        )

    @property
    def compound_tags(self):
        return {tag for tag in self.tags if self.KEY_VALUE_SEPARATOR in tag}

    @property
    def hierarchy_tags(self):
        return {tag for tag in self.tags if self.HIERARCHY_SEPARATOR in tag}

    def sanitize_variant_tag(
        self, param_name: str, param_index: int, param_value: Any
    ) -> str:
        if isinstance(param_value, tuple(TAGGABLE_TYPES)):
            sanitized_tag = f"{param_name}{self.KEY_VALUE_SEPARATOR}{param_value}"
        else:
            variant_value = f"variant-{param_index}"
            sanitized_tag = f"{param_name}{self.KEY_VALUE_SEPARATOR}{variant_value}"

        return sanitized_tag

    def from_variant(
        self, variant_kwargs: Dict[str, Any], variant_indexes: Dict[str, int] = None
    ) -> RegistrationKey:
        variant_tags = []
        variant_indexes = (
            {key: 1 for key in variant_kwargs}
            if variant_indexes is None
            else variant_indexes
        )
        for param_name, variant_value in variant_kwargs.items():
            if variant_indexes[param_name] == 0:
                continue

            if isinstance(variant_value, RegistrationKey):
                # The recursive approach of dag resolution ensures tag hierarchy
                for tag in variant_value.tags:
                    variant_tags.append(f"{param_name}{self.HIERARCHY_SEPARATOR}{tag}")
            else:
                variant_tags.append(
                    self.sanitize_variant_tag(
                        param_name=param_name,
                        param_index=variant_indexes[param_name],
                        param_value=variant_value,
                    )
                )

        return RegistrationKey(
            name=self.name,
            tags=self.tags.union(set(variant_tags)),
            namespace=self.namespace,
            special_tags=self.special_tags,
            description=self.description,
            metadata=self.metadata,
            resolve_automatically=self.resolve_automatically,
        )

    def from_tags_simplification(self, tags: Tags):
        """
        Builds a new ``RegistrationKey`` from current instance by removing provided tags.

        Args:
            tags: a Tag set containing tags to remove

        Returns:
            A ``RegistrationKey`` instance that is the same as the current instance
             but with ``tags`` removed.

        """
        remaining_tags = self.tags.difference(tags)
        return RegistrationKey(
            name=self.name, tags=remaining_tags, namespace=self.namespace
        )

    @classmethod
    def from_string(cls, string_format: str) -> RegistrationKey:
        """
        Parses a ``RegistrationKey`` instance from its string format.

        Args:
            string_format: the string format of a ``RegistrationKey`` instance.

        Returns:
            The corresponding parsed ``RegistrationKey`` instance
        """

        registration_attributes = string_format.split(cls.ATTRIBUTE_SEPARATOR)
        registration_dict = {}
        for registration_attribute in registration_attributes:
            try:
                key, value = registration_attribute.split(cls.KEY_VALUE_SEPARATOR)
                if key == "tags":
                    value = set(ast.literal_eval(value))

                registration_dict[key] = value
            except ValueError as e:
                logger.exception(
                    f"Failed parsing registration key from string.. "
                    f"Got: {string_format}"
                )
                raise e

        return RegistrationKey(**registration_dict)

    @classmethod
    def parse(
        cls,
        registration_key: Optional[Union[RegistrationKey, str]] = None,
        name: Optional[str] = None,
        namespace: Optional[str] = None,
        tags: Tags = None,
    ) -> RegistrationKey:
        """
        Parses a given ``RegistrationKey`` instance.
        If the given ``registration_key`` is in its string format, it is converted
         to ``RegistrationKey`` instance

        Args:
            registration_key: a ``RegistrationKey`` instance in its class instance
             or string format
            name: the ``name`` field of ``RegistrationKey``
            namespace: the ``namespace`` field of ``RegistrationKey``
            tags: the ``tags`` field of ``RegistrationKey``

        Returns:
            The parsed ``RegistrationKey`` instance
        """

        if registration_key is None and name is None:
            raise AttributeError("Expected either a registration key or its arguments")

        if isinstance(registration_key, RegistrationKey):
            return registration_key
        elif isinstance(registration_key, str):
            registration_key = RegistrationKey.from_string(
                string_format=registration_key
            )
        else:
            if name is None:
                raise AttributeError("Expected at least a registration key name")

            registration_key = RegistrationKey(
                name=name,
                tags=set(tags) if tags is not None else tags,
                namespace=namespace,
            )

        return registration_key

    def match(self, key: RegistrationKey, tags: Tags) -> bool:
        return self.tags.intersection(key.tags) == tags

    def toJSON(self):
        return (
            json.dumps(self.__str__(), sort_keys=True, indent=4)
            .replace('"', "")
            .replace("\\", "")
        )

    def to_pretty_string(self):
        tags = list(sorted(list(self.tags)))
        num_intervals = math.ceil(len(tags) / RegistrationKey.MAX_TAGS_PER_LINE)
        splits = list(batched(tags, num_intervals))
        tags = "\n".join([", ".join(item) for item in splits])

        return f"""[
                name: {self.name}
                tags: {tags}
                namespace: {self.namespace}
            ]
        """

    def to_record(
        self,
    ) -> Tuple[str, Optional[List[str]], str, Optional[str], Optional[str]]:
        return (
            self.name,
            sorted(self.tags),
            self.namespace,
            self.description,
            self.metadata,
        )


class BufferedRegistration:
    def __init__(
        self,
        func: Callable,
        name: str,
        namespace: str,
        tags: Tags = None,
        component: Optional[str] = None,
        run_method: Optional[str] = None,
        resolve_automatically: bool = True,
    ):
        self.func = func
        self.name = name
        self.namespace = namespace
        self.tags = tags
        self.component = component
        self.run_method = run_method
        self.resolve_automatically = resolve_automatically


def register_method(
    name: str,
    namespace: str,
    tags: Tags = None,
    component: Optional[str] = None,
    run_method: Optional[str] = None,
    resolve_automatically: bool = True,
) -> Callable:
    def register_wrapper(func):
        key = RegistrationKey(name=name, tags=tags, namespace=namespace)
        if (
            hasattr(Registry, "REGISTRATION_CONTEXT")
            and Registry.REGISTRATION_CONTEXT.is_registering
            and key not in Registry.REGISTRATION_METHODS
        ):
            Registry.REGISTRATION_METHODS[str(key)] = BufferedRegistration(
                func=func,
                name=name,
                tags=tags,
                namespace=namespace,
                component=component,
                run_method=run_method,
                resolve_automatically=resolve_automatically,
            )
        return func

    return register_wrapper


def register(func: Callable) -> Callable:
    filename = func.__code__.co_filename
    qualifier_name = func.__qualname__
    method_name = f"{filename}-{qualifier_name}"

    if (
        hasattr(Registry, "REGISTRATION_CONTEXT")
        and Registry.REGISTRATION_CONTEXT.is_registering
        and method_name not in Registry.REGISTRATION_METHODS
    ):
        Registry.REGISTRATION_METHODS[method_name] = func
    return func


class RegistrationContext:
    def __init__(self):
        self.is_registering: bool = False

    def __enter__(self):
        self.is_registering = True

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.is_registering = False


@dataclass
class ConfigurationInfo:
    """
    Utility dataclass used for registration.
    The ``Configuration`` class is stored in the Registry via its corresponding
     ``ConfigurationInfo`` wrapper.

    This wrapper contains:
        - config: ``Configuration`` instance
        - component: the ``Component`` class type as string
        - run_method: if any, the ``Component`` method to execute when instantiating the
         ``Component`` as runnable
    """

    config: cinnamon.configuration.Configuration
    component: Optional[str] = None
    run_method: Optional[str] = None


class Registry:
    """
    The registration registry.
    The registry has three main functionalities:
    - Storing/Retrieving registered ``Configuration``: via the ``ConfigurationInfo``
     internal wrapper.
    - Storing/Retrieving ``Configuration`` to ``Component`` bindings: the binding
     operation allows to build a ``Component`` instance from its
      registered ``Configuration``.
    - Storing/Retrieving registered built ``Component`` instances: a ``Component``
     instance can be registered as well to mimic Singleton behaviors.
     This functionality is useful is a single ``Component`` instance
       is used multiple times in a program.

    All the above functionalities require to specify a ``RegistrationKey``
     (either directly or indirectly).
    """

    _CONFIGURATION_FOLDER = "configurations"

    _REGISTRY: Dict[RegistrationKey, ConfigurationInfo]

    _ROOT_KEY = RegistrationKey(name="root", namespace="root")
    _DEPENDENCY_DAG: nx.DiGraph

    expanded: bool = False

    _MODULES: List[Union[str, Path]]
    _EXP_MODULES: Set[Path]
    _MODULE_MAPPING: Dict[str, str]
    _EXP_NAMESPACES: List[str]

    REGISTRATION_METHODS: Dict[str, Callable | BufferedRegistration]
    REGISTRATION_CONTEXT: RegistrationContext

    @classmethod
    def initialize(cls):
        cls._REGISTRY = {}

        cls.REGISTRATION_METHODS = {}
        cls.REGISTRATION_CONTEXT = RegistrationContext()
        cls._EXP_MODULES = set()
        cls._MODULE_MAPPING = {}
        cls._EXP_NAMESPACES = []

        cls.expanded = False

        cls._DEPENDENCY_DAG = nx.DiGraph()
        cls._DEPENDENCY_DAG.add_node(cls._ROOT_KEY)

    @classmethod
    @time_it
    def build(
        cls,
        directory: Union[Path, AnyStr],
        external_directories: List[Union[AnyStr, Path]] = None,
    ) -> Tuple[Set[RegistrationKey], Set[RegistrationKey]]:
        """
        Main entrypoint of cinnamon.
        The registry checks provided directories for configurations to populate its
         internal registry and build the dependency DAG.
        Eventually, the dependency DAG is expanded to account for variants
         and invalid configurations.

        Args:
            directory: the main directory of the project containing configurations.
            external_directories: external directories containing configurations.

        Returns:
            valid_keys: a ``ResolutionInfo` containing valid ``RegistrationKey``
            invalid_keys: a ``ResolutionInfo` containing invalid ``RegistrationKey``

        Raises:
           ``RuntimeWarning``: if duplicate namespaces are found.

           ``InvalidDirectoryException``: if one of the provided directories does
            not exist or is not a directory.

           ``AlreadyExpandedException``: if the dependency DAG has been expanded.

           ``NotADAGException``: if the dependency DAG is not a DAG.

           ``DisconnectedGraphException``: if, for some reason, the dependency DAG
            contains disconnected nodes.
           This should never happen via cinnamon APIs, unless some manual intervention
            on the dependency DAG is carried out.
        """

        directory = Path(directory).resolve()

        cls.initialize()

        local_namespaces, local_module_mapping = cls.parse_configuration_files(
            directories=[directory]
        )
        cls.update_namespaces(
            namespaces=local_namespaces, module_mapping=local_module_mapping
        )

        if external_directories is not None:
            external_directories = cls.resolve_external_directories(
                external_directories=external_directories
            )
            cls._MODULES = external_directories
            ext_namespaces, ext_module_mapping = cls.parse_configuration_files(
                directories=external_directories
            )
            cls.update_namespaces(
                namespaces=ext_namespaces, module_mapping=ext_module_mapping
            )

        cls.load_registrations(directory=directory)
        valid_keys, invalid_keys = cls.dag_resolution()

        cls._REGISTRY = {
            key: value for key, value in cls._REGISTRY.items() if key in valid_keys
        }

        return valid_keys, invalid_keys

    @classmethod
    @time_it
    def update_namespaces(
        cls, namespaces: List[str], module_mapping: Dict[str, List[str]]
    ):
        for key in module_mapping:
            if key in cls._MODULE_MAPPING:
                raise RuntimeWarning(
                    f"Found duplicate namespace: {key}. Overriding existing mapping..."
                )

        cls._EXP_NAMESPACES.extend(namespaces)
        cls._MODULE_MAPPING = {**cls._MODULE_MAPPING, **module_mapping}

    @classmethod
    @time_it
    def parse_configuration_files(
        cls, directories: List[Path]
    ) -> Tuple[List[str], Dict[str, List[str]]]:
        """
        Runs a static code analyzer to inspect code scripts containing
         cinnamon registrations with the goal of determining unique namespaces.

        Args:
            directories: list of directories containing cinnamon registrations.

        Returns:
            namespaces: unique list of namespaces
            mapping: mapping from namespace to pathlib.Path directories.
        """

        extractor = NamespaceExtractor()
        namespaces = []
        mapping = {}
        for directory in directories:
            for config_folder in directory.rglob(Registry._CONFIGURATION_FOLDER):
                for python_script in config_folder.glob("*.py"):
                    dir_namespaces = extractor.process(filename=python_script)
                    namespaces.extend(dir_namespaces)
                    mapping = {
                        **mapping,
                        **{namespace: directory for namespace in dir_namespaces},
                    }

        namespaces = list(set(namespaces))
        return namespaces, mapping

    @classmethod
    @time_it
    def resolve_external_directories(
        cls,
        external_directories: List[Union[AnyStr, Path]],
    ) -> List[Path]:
        """
        Checks if provided directories are valid directories and exist.

        Args:
            external_directories: directories to validate.

        Returns:
            resolved_directories: validated directories as pathlib.Path instances

        Raises:
            ``InvalidDirectoryException``: if any of the provided directories is
             not a directory or does not exist.
        """

        resolved_directories = []
        for directory in external_directories:
            directory = Path(directory)
            if not directory.exists() or not directory.is_dir():
                raise InvalidDirectoryException(directory=directory)
            resolved_directories.append(directory)

        return resolved_directories

    @classmethod
    @time_it
    def load_registrations(
        cls,
        directory: Union[AnyStr, Path],
    ):
        """
        Imports a Python's module for registration.
        The Registry looks for ``register()`` and ``register_method()`` decorators.
        These functions are the entry points for registrations: that is, where the
         ``Registry`` APIs are invoked to issue registrations.

        Args:
            directory: path of the module

        Raises:
            ``InvalidDirectoryException``: if the provided directory is not a directory
             or does not exist.
        """
        directory = Path(directory)

        if not directory.exists() or not directory.is_dir():
            raise InvalidDirectoryException(directory=directory)

        if directory in cls._EXP_MODULES:
            return

        # Add directory to PYTHONPATH
        sys.path.insert(0, directory.as_posix())

        cls._EXP_MODULES.add(directory)

        with cls.REGISTRATION_CONTEXT:
            for python_script in directory.rglob("*.py"):
                if cls._CONFIGURATION_FOLDER not in python_script.parts:
                    continue

                spec = importlib.util.spec_from_file_location(
                    name=python_script.name, location=python_script
                )

                if spec is None:
                    logging.error(f"Could not load {python_script}.")
                    raise RuntimeError(f"Could not load {python_script}.")

                # import module and run registration methods
                current_keys = set(cls.REGISTRATION_METHODS.keys())

                try:
                    module = importlib.util.module_from_spec(spec=spec)
                    spec.loader.exec_module(module)
                except Exception as e:
                    logging.error(f"Failed to execute module {python_script.name}. {e}")
                    raise RuntimeError(
                        f"Failed to execute module {python_script.name}. {e}"
                    )

                new_keys = set(cls.REGISTRATION_METHODS.keys()).difference(current_keys)

                module_dict = module.__dict__
                for key in new_keys:
                    key_method = cls.REGISTRATION_METHODS[key]
                    if isinstance(key_method, BufferedRegistration):
                        qual_parts = key_method.func.__qualname__.split(".")
                        method_name = qual_parts[-1]
                        class_method_name = qual_parts[-2]

                        class_method = module_dict[class_method_name]

                        Registry.register_configuration(
                            config=getattr(class_method, method_name)(),
                            name=key_method.name,
                            tags=key_method.tags,
                            namespace=key_method.namespace,
                            component=key_method.component,
                            run_method=key_method.run_method,
                            resolve_automatically=key_method.resolve_automatically,
                        )
                    else:
                        cls.REGISTRATION_METHODS[key]()

    @classmethod
    def in_registry(
        cls,
        registration_key: RegistrationKey,
    ) -> bool:
        return registration_key in cls._REGISTRY

    @classmethod
    def is_namespace_covered(cls, registration_key: RegistrationKey) -> bool:
        return registration_key.namespace in cls._EXP_NAMESPACES

    @classmethod
    def in_graph(
        cls,
        registration_key: Optional[Registration] = None,
        name: Optional[str] = None,
        namespace: Optional[str] = None,
        tags: Tags = None,
    ) -> bool:
        registration_key = RegistrationKey.parse(
            registration_key=registration_key, name=name, tags=tags, namespace=namespace
        )
        return registration_key in cls._DEPENDENCY_DAG

    # DAG Resolution APIs

    @classmethod
    def check_registration_graph(cls) -> bool:
        """
        Checks if the dependency DAG is valid.

        Raises:
           ``AlreadyExpandedException``: if the dependency DAG has been expanded.

           ``NotADAGException``: if the dependency DAG is not a DAG.

           ``DisconnectedGraphException``: if, for some reason, the dependency DAG
            contains disconnected nodes.
           This should never happen via cinnamon APIs, unless some manual intervention
            on the dependency DAG is carried out.
        """

        if cls.expanded:
            raise AlreadyExpandedException()

        # check if DAG is DAG
        if not nx.is_directed_acyclic_graph(cls._DEPENDENCY_DAG):
            raise NotADAGException(edges=cls._DEPENDENCY_DAG.edges)

        # check if isolated nodes
        isolated_nodes = list(nx.isolates(cls._DEPENDENCY_DAG))
        if len(isolated_nodes) > 0 and len(cls._DEPENDENCY_DAG.nodes) > 1:
            raise DisconnectedGraphException(nodes=isolated_nodes)

        return True

    @classmethod
    @time_it
    def dag_resolution(cls) -> Tuple[Set[RegistrationKey], Set[RegistrationKey]]:
        """
        Expands and resolves dependencies in registration DAG.
        The dependency traversal is done bottom-up by recursively expanding top nodes
        (i.e., ``RegistrationKey`` instances).
        Expanded keys are retrieved, and built for full validation.

        Returns:
            valid_keys: the set of valid registration keys
            invalid_keys:the set of invalid registration keys
        """

        cls.check_registration_graph()

        # Variants expansion doesn't change the topology of the graph
        valid_key_buffer: Set[RegistrationKey] = set()
        invalid_key_buffer: Set[RegistrationKey] = set()
        logging.info(f"Resolving {len(cls._REGISTRY)} configurations...")
        for key in cls._DEPENDENCY_DAG.successors(cls._ROOT_KEY):
            Registry.expand_configuration(
                key=key,
                valid_key_buffer=valid_key_buffer,
                invalid_key_buffer=invalid_key_buffer,
            )

        cls.expanded = True

        return valid_key_buffer, invalid_key_buffer

    @classmethod
    def expand_configuration(
        cls,
        key: RegistrationKey,
        valid_key_buffer: Set[RegistrationKey] = None,
        invalid_key_buffer: Set[RegistrationKey] = None,
    ) -> Set[RegistrationKey]:
        valid_key_buffer = valid_key_buffer if valid_key_buffer is not None else set()
        invalid_key_buffer = (
            invalid_key_buffer if invalid_key_buffer is not None else set()
        )

        config_info = cls.retrieve_configuration_info(registration_key=key)
        config = config_info.config

        # We retrieve all keys related to input key through dependency DAG
        if config.expanded:
            keys = {edge[1] for edge in cls._DEPENDENCY_DAG.out_edges(key)}.union({key})
            return keys

        keys = set()

        # dependencies
        for dependency_name, dependency in config.dependencies.items():
            dependency_variants = set()

            # if dependency returns multiple keys, we keep the first as the main one
            # and the rest is moved to variants
            if dependency is not None and isinstance(dependency, RegistrationKey):
                dependency_keys = Registry.expand_configuration(
                    key=dependency,
                    valid_key_buffer=valid_key_buffer,
                    invalid_key_buffer=invalid_key_buffer,
                )
                dependency_variants = dependency_variants.union(
                    dependency_keys
                ).difference({dependency})

            for key_variant in config.meta[dependency_name].variants:
                if key_variant is not None and isinstance(key_variant, RegistrationKey):
                    dependency_variants = dependency_variants.union(
                        Registry.expand_configuration(
                            key=key_variant,
                            valid_key_buffer=valid_key_buffer,
                            invalid_key_buffer=invalid_key_buffer,
                        )
                    )

            config.meta[dependency_name].variants = list(dependency_variants)

        # variants
        for variant_info in config.variants:
            variant_key = key.from_variant(
                variant_kwargs=variant_info['values'],
                variant_indexes=variant_info['indexes']
            )

            if not cls.in_graph(variant_key):
                cls._DEPENDENCY_DAG.add_node(variant_key)
            cls._DEPENDENCY_DAG.add_edge(key, variant_key, type="variant")

            try:
                variant_config = config.model_copy(update=variant_info['values'],
                                                   deep=True)
            except pydantic.ValidationError as validation_result:
                variant_key.metadata = repr(validation_result)
                invalid_key_buffer.add(variant_key)
                continue

            if not Registry.in_registry(variant_key):
                cls.register_configuration(
                    config=variant_config,
                    name=variant_key.name,
                    tags=variant_key.tags,
                    namespace=variant_key.namespace,
                    component=config_info.component,
                    run_method=config_info.run_method,
                    resolve_automatically=variant_key.resolve_automatically,
                )

            # If resolve_automatically is enabled we still have to resolve a copy of it
            # to check its validity
            # Otherwise, we risk in registering keys that are invalid as valid
            if not variant_key.resolve_automatically:
                resolved_config = Registry.resolve_configuration(
                    config=variant_config.model_copy(deep=True)
                )
                validation_result = resolved_config.validate_conditions(strict=False)
            else:
                variant_config = Registry.resolve_configuration(config=variant_config)
                validation_result = variant_config.validate_conditions(strict=False)

            if validation_result.passed:
                keys.add(variant_key)
                valid_key_buffer.add(variant_key)
            else:
                variant_key.metadata = validation_result.stack_trace
                invalid_key_buffer.add(variant_key)

        if not key.resolve_automatically:
            resolved_config = Registry.resolve_configuration(
                config=config.model_copy(deep=True)
            )
            validation_result = resolved_config.validate_conditions(strict=False)
        else:
            config = Registry.resolve_configuration(config=config)
            validation_result = config.validate_conditions(strict=False)

        if validation_result.passed:
            valid_key_buffer.add(key)
            keys.add(key)
        else:
            key.metadata = validation_result.stack_trace
            invalid_key_buffer.add(key)

        config.expanded = True

        return keys

    # Registration APIs

    # Component

    @classmethod
    def instantiate_component(
        cls,
        registration_key: Optional[Registration] = None,
        name: Optional[str] = None,
        namespace: Optional[str] = None,
        tags: Tags = None,
        **build_args,
    ) -> cinnamon.component.Component:
        """
        Builds a ``Component`` instance from its bounded ``Configuration``
         via the implicit ``RegistrationKey``.

        Args:
            registration_key: the ``RegistrationKey`` used to register the
             ``Configuration`` class.
            name: the ``name`` attribute of ``RegistrationKey``
            tags: the ``tags`` attribute of ``RegistrationKey``
            namespace: the ``namespace`` attribute of ``RegistrationKey``
            build_args: additional custom component constructor args

        Returns:
            The built ``Component`` instance

        Raises:
            ``InvalidConfigurationTypeException``: if there's a mismatch between
             the ``Configuration`` class used during registration and the type of the
              built ``Configuration`` instance using the registered
            ``constructor`` method (see ``ConfigurationInfo`` arguments).

            ``NotBoundException``: if the ``Configuration`` is not bound to
             any ``Component``.
        """
        if not cls.expanded:
            raise NotExpandedException()

        registration_key: RegistrationKey = RegistrationKey.parse(
            registration_key=registration_key, name=name, tags=tags, namespace=namespace
        )

        if not cls.in_registry(registration_key=registration_key):
            raise NotRegisteredException(registration_key=registration_key)

        config_info: ConfigurationInfo = cls._REGISTRY[registration_key]
        config = config_info.config

        if config_info.component is None:
            raise NotBoundException(registration_key=registration_key)

        component_args = {**config.fields, **build_args}
        component_class = import_class_from_string(config_info.component)
        component = component_class(**component_args)

        return component

    # Configuration

    @classmethod
    def register_configuration(
        cls,
        config: cinnamon.configuration.Configuration,
        name: str,
        namespace: str,
        tags: Tags = None,
        component: Optional[str] = None,
        resolve_automatically: bool = True,
        run_method: Optional[str] = None,
    ):
        """
        Registers a ``Configuration`` in the registry.
        In particular, a ``ConfigurationInfo`` wrapper is stored in the ``Registry``.

        Args:
            config: `Configuration`` instance
            name: the ``name`` field of ``RegistrationKey``
            namespace: the ``namespace`` field of ``RegistrationKey``
            tags: the ``tags`` field of ``RegistrationKey``,
            component: ``Component`` module path as string
            resolve_automatically: whether the RegistrationKey has to be
             resolved automatically during DAG resolution or not
            run_method: ``Component`` method to run when instantiating
             the ``Component`` as runnable

        Returns:
            The built ``RegistrationKey`` instance that can be used to retrieve
             the registered ``ConfigurationInfo``.

        Raises:
            ``NotExpandedException``: if the dependency DAG has not been expanded yet.

            ``AlreadyRegisteredException``: if the ``RegistrationKey`` is already used

            ``NamespaceNotFoundException``: if one of the dependencies of
             ``RegistrationKey`` belongs to a namespace not covered.
        """
        if cls.expanded:
            raise AlreadyExpandedException()

        registration_key = RegistrationKey(
            name=name,
            tags=tags,
            namespace=namespace,
            resolve_automatically=resolve_automatically,
        )

        # Check if already registered
        if cls.in_registry(registration_key=registration_key):
            raise AlreadyRegisteredException(registration_key=registration_key)

        # Store configuration in registry
        cls._REGISTRY[registration_key] = ConfigurationInfo(
            config=config, component=component, run_method=run_method
        )
        if run_method is not None:
            registration_key.special_tags.add("__runnable")

        # Add to dependency graph
        cls._DEPENDENCY_DAG.add_node(registration_key)
        if not len(cls._DEPENDENCY_DAG.in_edges(registration_key)):
            cls._DEPENDENCY_DAG.add_edge(cls._ROOT_KEY, registration_key, type="child")

        # include dependencies
        for dependency_name, dependency in config.dependencies.items():
            dependency_param = config.fields[dependency_name]
            assert isinstance(dependency, RegistrationKey)

            dependency_key = dependency
            dependency_variants: list[RegistrationKey] = config.meta[
                dependency_name
            ].variants
            dependencies = (
                [dependency_key] + dependency_variants
                if dependency_key is not None
                else dependency_variants
            )
            for dep in dependencies:
                if not isinstance(dep, RegistrationKey):
                    continue

                if not cls.in_graph(dep):
                    cls._DEPENDENCY_DAG.add_node(dep)

                cls._DEPENDENCY_DAG.add_edge(registration_key, dep, type="child")

                if dep.namespace != namespace:
                    if not cls.is_namespace_covered(dep):
                        raise NamespaceNotFoundException(
                            registration_key=registration_key,
                            namespaces=cls._EXP_NAMESPACES,
                        )
                    cls.load_registrations(directory=cls._MODULE_MAPPING[dep.namespace])

        return registration_key

    @classmethod
    def resolve_configuration(
        cls, config: cinnamon.configuration.Configuration
    ) -> cinnamon.configuration.Configuration:
        for dependency_name, dependency in config.dependencies.items():
            if dependency is not None and isinstance(dependency, RegistrationKey):
                dependency.value = Registry.retrieve_configuration(
                    registration_key=dependency
                )

            config.meta[dependency_name].variants = [
                Registry.retrieve_configuration(registration_key=variant_key)
                if isinstance(variant_key, RegistrationKey)
                else variant_key
                for variant_key in config.meta[dependency_name].variants
            ]

        return config

    @classmethod
    def _retrieve(
        cls,
        registration_key: Optional[Registration] = None,
        name: Optional[str] = None,
        namespace: Optional[str] = None,
        tags: Tags = None,
    ) -> ConfigurationInfo:
        """
            Retrieves a ``ConfigurationInfo`` instance from the registry via
             its ``RegistrationKey``.

        Args:
            registration_key: key used to register the configuration
            name: the ``name`` field of ``RegistrationKey``
            namespace: the ``namespace`` field of ``RegistrationKey``
            tags: the ``tags`` field of ``RegistrationKey``

        Returns:
            config: the built configuration instance
        """

        registration_key: RegistrationKey = RegistrationKey.parse(
            registration_key=registration_key, name=name, tags=tags, namespace=namespace
        )

        if not cls.in_registry(registration_key=registration_key):
            raise NotRegisteredException(registration_key=registration_key)

        config_info: ConfigurationInfo = cls._REGISTRY[registration_key]
        return config_info

    @classmethod
    def retrieve_configuration(
        cls,
        registration_key: Optional[Registration] = None,
        name: Optional[str] = None,
        namespace: Optional[str] = None,
        tags: Tags = None,
    ) -> cinnamon.configuration.C:
        """
            Retrieves a ``Configuration`` instance from the registry
             via its ``RegistrationKey``.

        Args:
            registration_key: key used to register the configuration
            name: the ``name`` field of ``RegistrationKey``
            namespace: the ``namespace`` field of ``RegistrationKey``
            tags: the ``tags`` field of ``RegistrationKey``

        Returns:
            config: the built configuration instance
        """
        return cls._retrieve(
            registration_key=registration_key, name=name, namespace=namespace, tags=tags
        ).config

    @classmethod
    def retrieve_configuration_info(
        cls,
        registration_key: Optional[Registration] = None,
        name: Optional[str] = None,
        namespace: Optional[str] = None,
        tags: Tags = None,
    ) -> ConfigurationInfo:
        """
            Retrieves a ``Configuration`` instance from the registry
             via its ``RegistrationKey``.

        Args:
            registration_key: key used to register the configuration
            name: the ``name`` field of ``RegistrationKey``
            namespace: the ``namespace`` field of ``RegistrationKey``
            tags: the ``tags`` field of ``RegistrationKey``

        Returns:
            config: the built configuration instance
        """
        return cls._retrieve(
            registration_key=registration_key, name=name, namespace=namespace, tags=tags
        )

    @classmethod
    def retrieve_keys(
        cls,
        names: Optional[Union[List[str], str]] = None,
        namespaces: Optional[Union[List[str], str]] = None,
        tags: Tags = None,
        special_tags: Tags = None,
        keys: List[RegistrationKey] = None,
    ) -> List[RegistrationKey]:
        """
        Retrieves ``RegistrationKey`` via given name, tags, namespaces filters.
        The search can be limited to a fixed set of keys, optionally given in input.

        Args:
            names: a name or a list of names to filter registration keys.
            namespaces: a namespace or a list of namespaces to filter registration keys.
            tags: a tag set to filter registration keys.
            special_tags: a special tag set to filter registration keys.
            keys: an optional list of ``RegistrationKey`` on which to apply the search.

        Returns:
        """

        keys = keys if keys is not None else cls._REGISTRY.keys()

        return [
            key
            for key in keys
            if match_name(name=key.name, names=names)
            and match_namespace(namespace=key.namespace, namespaces=namespaces)
            and match_tags(a_tags=key.tags, b_tags=tags)
            and match_tags(a_tags=key.special_tags, b_tags=special_tags)
        ]

    @classmethod
    def retrieve_runnable_keys(cls) -> List[RegistrationKey]:
        return cls.retrieve_keys(special_tags={"__runnable"})
