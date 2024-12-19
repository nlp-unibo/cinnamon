from __future__ import annotations

import ast
import importlib.util
import json
import os
import sys
from dataclasses import dataclass
from logging import getLogger
from pathlib import Path
from typing import Type, AnyStr, List, Dict, Any, Union, Optional, Callable, Tuple, Set

import git
import networkx as nx

import cinnamon.component
import cinnamon.configuration
from cinnamon.utility.registration import NamespaceExtractor

logger = getLogger(__name__)

Constructor = Callable[[], 'cinnamon.configuration.Configuration']

__all__ = [
    'RegistrationKey',
    'register',
    'register_method',
    'Registry',
    'Registration',
    'ConfigurationInfo',
    'NotRegisteredException',
    'NotBoundException',
    'AlreadyRegisteredException',
    'InvalidConfigurationTypeException',
    'AlreadyExpandedException',
    'NotExpandedException',
    'DisconnectedGraphException',
    'NotADAGException',
    'InvalidDirectoryException',
    'NamespaceNotFoundException'
]


class RegistrationKey:
    """
    Compound key used for registration.
    """

    KEY_VALUE_SEPARATOR: str = ':'
    ATTRIBUTE_SEPARATOR: str = '--'

    def __init__(
            self,
            name: str,
            namespace: str,
            tags: cinnamon.configuration.Tags = None,
            description: Optional[str] = None,
            metadata: Optional[str] = None
    ):
        """

        Args:
            name: A general identifier of the type of ``Configuration`` being registered.
                For example, use ``name='data_loader'`` if you are registering a data loader ``Configuration``.
                Note that this is the recommended naming convention. There are no specific restrictions regarding
                name choice.
            namespace: The namespace is a high-level identifier used to distinguish macro groups
                of registered Configuration. For example, a group of models may be implemented in Tensorflow and
                another one in Torch. You can distinguish between these two groups by specifying two
                distinct namespaces. Additionally, the namespace can also used to distinguish among
                multiple users' registrations. In this case, the recommended naming convention is
                like the Huggingface's one: ``user/namespace``.
            tags: tags are metadata information that allows quick inspection of a registered ``Configuration`` details.
                In the case of ``Configuration`` with the same name and namespace (e.g., multiple models implemented by
                the same user), tags are used to distinguish among them.
        """
        self.name = name
        self.namespace = namespace if namespace is not None else 'default'
        self.tags = tags if tags is not None else set()
        self.description = description
        self.metadata = metadata

    def __hash__(
            self
    ) -> int:
        return hash(self.__str__())

    def __str__(
            self
    ) -> str:
        to_return = [f'name{self.KEY_VALUE_SEPARATOR}{self.name}']

        if self.tags is not None:
            tags = sorted(list(self.tags)) if self.tags else None
            if tags is not None:
                to_return.append(f'{self.ATTRIBUTE_SEPARATOR}tags{self.KEY_VALUE_SEPARATOR}{tags}')

        to_return.append(f'{self.ATTRIBUTE_SEPARATOR}namespace{self.KEY_VALUE_SEPARATOR}{self.namespace}')
        return ''.join(to_return)

    def __repr__(
            self
    ) -> str:
        return self.__str__()

    def __eq__(
            self,
            other
    ) -> bool:
        if other is None or not isinstance(other, RegistrationKey):
            return False

        default_condition = lambda other: self.name == other.name

        tags_condition = lambda other: (self.tags is not None and other.tags is not None and self.tags == other.tags) \
                                       or (self.tags is None and other.tags is None)

        namespace_condition = lambda other: (self.namespace is not None
                                             and other.namespace is not None
                                             and self.namespace == other.namespace) \
                                            or (self.namespace is None and other.namespace is None)

        return default_condition(other) \
            and tags_condition(other) \
            and namespace_condition(other)

    @property
    def compound_tags(
            self
    ):
        return {tag for tag in self.tags if self.KEY_VALUE_SEPARATOR in tag}

    def from_variant(
            self,
            variant_kwargs: Dict[str, Any]
    ):
        variant_tags = []
        for param_name, variant_value in variant_kwargs.items():
            # TODO: what if the namespace of this child is different?
            if type(variant_value) == RegistrationKey:
                variant_tags.extend(variant_value.tags)
            else:
                variant_tags.append(f'{param_name}={variant_value}')

        return RegistrationKey(name=self.name,
                               tags=self.tags.union(set(variant_tags)),
                               namespace=self.namespace)

    @classmethod
    def from_string(
            cls,
            string_format: str
    ) -> RegistrationKey:
        """
        Utility method to parse a ``RegistrationKey`` instance from its string format.

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
                if key == 'tags':
                    value = set(ast.literal_eval(value))

                registration_dict[key] = value
            except ValueError as e:
                logger.exception(f'Failed parsing registration key from string.. Got: {string_format}')
                raise e

        return RegistrationKey(**registration_dict)

    @classmethod
    def parse(
            cls,
            registration_key: Optional[Union[RegistrationKey, str]] = None,
            name: Optional[str] = None,
            namespace: Optional[str] = None,
            tags: cinnamon.configuration.Tags = None,
    ) -> RegistrationKey:
        """
        Parses a given ``RegistrationKey`` instance.
        If the given ``registration_key`` is in its string format, it is converted to ``RegistrationKey`` instance

        Args:
            registration_key: a ``RegistrationKey`` instance in its class instance or string format
            name: the ``name`` field of ``RegistrationKey``
            namespace: the ``namespace`` field of ``RegistrationKey``
            tags: the ``tags`` field of ``RegistrationKey``

        Returns:
            The parsed ``RegistrationKey`` instance
        """

        if registration_key is None and name is None:
            raise AttributeError(f'Expected either a registration key or its arguments')

        if type(registration_key) == RegistrationKey:
            return registration_key
        elif type(registration_key) == str:
            registration_key = RegistrationKey.from_string(string_format=registration_key)
        else:
            if name is None:
                raise AttributeError(f'Expected at least a registration key name')

            registration_key = RegistrationKey(name=name,
                                               tags=set(tags) if tags is not None else tags,
                                               namespace=namespace)

        return registration_key

    def toJSON(
            self
    ):
        return json.dumps(
            self.__str__(),
            sort_keys=True,
            indent=4
        ).replace("\"", '').replace("\\", "")

    def to_record(
            self
    ) -> Tuple[str, Optional[List[str]], str, Optional[str], Optional[str]]:
        return (
            self.name,
            sorted(self.tags),
            self.namespace,
            self.description,
            self.metadata
        )


Registration = Union[RegistrationKey, str]


class AlreadyRegisteredException(Exception):

    def __init__(
            self,
            registration_key: RegistrationKey
    ):
        super(AlreadyRegisteredException, self).__init__(
            f'A configuration has already been registered with the same key!'
            f'Got: {registration_key}')


class NamespaceNotFoundException(Exception):

    def __init__(
            self,
            registration_key: RegistrationKey,
            namespaces: List[str]
    ):
        super(NamespaceNotFoundException, self).__init__(
            f'The given registration key contains a namespace that cannot be found. {os.linesep}'
            f'Key: {registration_key}{os.linesep}'
            f'Namespaces: {namespaces}')


class NotRegisteredException(Exception):

    def __init__(
            self,
            registration_key: RegistrationKey
    ):
        super(NotRegisteredException, self).__init__(f"Could not find registered configuration {registration_key}."
                                                     f" Did you register it?")


class NotBoundException(Exception):

    def __init__(
            self,
            registration_key: RegistrationKey
    ):
        super(NotBoundException, self).__init__(
            f'Registered configuration {registration_key} is not bound to any component.'
            f' Did you bind it?')


class InvalidConfigurationTypeException(Exception):

    def __init__(
            self,
            expected_type: Type,
            actual_type: Type
    ):
        super(InvalidConfigurationTypeException, self).__init__(
            f"Expected to build configuration of type {expected_type} but got {actual_type}")


class DisconnectedGraphException(Exception):

    def __init__(
            self,
            nodes
    ):
        super().__init__(f'Disconnected graph! Nodes {nodes} are not connected!')


class NotADAGException(Exception):

    def __init__(
            self,
            edges
    ):
        super().__init__(f'The built graph is not a DAG! {os.linesep}'
                         f'Please find below the edge list: {os.linesep}'
                         f'{self.build_edge_view(edges)}')

    def build_edge_view(
            self,
            edges
    ):
        view = []
        for edge in edges:
            node_view = f'{edge[0]} -> {edge[1]}'
            view.append(node_view)
        return os.linesep.join(view)


class AlreadyExpandedException(Exception):

    def __init__(
            self
    ):
        super().__init__(f'The registration graph has already been expanded! No further registrations are allowed.')


class NotExpandedException(Exception):

    def __init__(
            self
    ):
        super().__init__(f'The registration graph has yet to be expanded! Configuration retrieval is not allowed.')


class InvalidDirectoryException(Exception):

    def __init__(
            self,
            directory: Union[AnyStr, Path]
    ):
        super().__init__(f'The provided directory path does not exist or is not a directory. {os.linesep}'
                         f'Path: {directory}')


@dataclass
class ConfigurationInfo:
    """
    Utility dataclass used for registration.
    Behind the curtains, the ``Configuration`` class is stored in the Registry via its corresponding
    ``ConfigurationInfo`` wrapper.

    This wrapper containsL
        - class_type: the ``Configuration`` class type
        - constructor: the method for creating an instance from the specified ``class_type``.
            By default, the constructor is set to ``Configuration.get_default()`` method.
    """

    config_class: Type[cinnamon.configuration.Configuration]
    constructor: Constructor
    component_class: Type[cinnamon.component.Component]
    build_recursively: bool


class BufferedRegistration:

    def __init__(
            self,
            func: Callable,
            name: str,
            namespace: str,
            tags: cinnamon.configuration.Tags = None,
            component_class: Optional[Type[cinnamon.component.Component]] = None,
            build_recursively: bool = True
    ):
        self.func = func
        self.name = name
        self.namespace = namespace
        self.tags = tags
        self.component_class = component_class
        self.build_recursively = build_recursively

    def __call__(
            self,
    ):
        pass


def register_method(
        name: str,
        namespace: str,
        tags: cinnamon.configuration.Tags = None,
        component_class: Optional[Type[cinnamon.component.Component]] = None,
        build_recursively: bool = True
) -> Callable:
    def register_wrapper(func):
        key = RegistrationKey(name=name, tags=tags, namespace=namespace)
        if Registry.REGISTRY_MODE and key not in Registry.REGISTRATION_METHODS:
            Registry.REGISTRATION_METHODS[str(key)] = BufferedRegistration(
                func=func,
                name=name,
                tags=tags,
                namespace=namespace,
                component_class=component_class,
                build_recursively=build_recursively
            )
        return func

    return register_wrapper


def register(
        func: Callable
) -> Callable:
    filename = func.__code__.co_filename
    qualifier_name = func.__qualname__
    method_name = f'{filename}-{qualifier_name}'

    if Registry.REGISTRY_MODE and method_name not in Registry.REGISTRATION_METHODS:
        Registry.REGISTRATION_METHODS[method_name] = func
    return func


class Registry:
    """
    The registration registry.
    The registry has three main functionalities:
    - Storing/Retrieving registered ``Configuration``: via the ``ConfigurationInfo`` internal wrapper.
    - Storing/Retrieving ``Configuration`` to ``Component`` bindings: the binding operation allows to build
    a ``Component`` instance from its registered ``Configuration``.
    - Storing/Retrieving registered built ``Component`` instances: a ``Component`` instance can be registered
    as well to mimic Singleton behaviours. This functionality is useful is a single ``Component`` instance
    is used multiple times in a program.

    All the above functionalities require to specify a ``RegistrationKey`` (either directly or indirectly).
    """

    _REGISTRY: Dict[RegistrationKey, ConfigurationInfo]

    _ROOT_KEY = RegistrationKey(name='root', namespace='root')
    _DEPENDENCY_DAG: nx.DiGraph

    # TODO: we can set this a protected and define a DEBUG_MODE flag that allows __setattr__ of expanded
    expanded: bool = False

    _MODULES: List[Union[AnyStr, Path]]
    _EXP_MODULES: List[str]
    _MODULE_MAPPING: Dict[str, str]
    _EXP_NAMESPACES: List[str]

    REGISTRATION_METHODS: Dict[str, Callable]
    REGISTRY_MODE: bool = False

    @classmethod
    def initialize(
            cls
    ):
        cls._REGISTRY = {}

        cls.REGISTRATION_METHODS = {}
        cls._EXP_MODULES = []
        cls._MODULE_MAPPING = {}
        cls._EXP_NAMESPACES = []

        cls.expanded = False

        cls._DEPENDENCY_DAG = nx.DiGraph()
        cls._DEPENDENCY_DAG.add_node(cls._ROOT_KEY)

    @classmethod
    def setup(
            cls,
            directory: Union[Path, AnyStr] = None,
            external_directories: List[Union[AnyStr, Path]] = None,
            save_directory: Union[Path, AnyStr] = None
    ) -> Tuple[List[RegistrationKey], List[RegistrationKey]]:
        directory = Path(directory).resolve() if type(directory) != Path else directory
        if save_directory is not None:
            save_directory = Path(save_directory).resolve() if type(
                save_directory) != Path else directory.parent.resolve()
        else:
            save_directory = directory.parent.resolve()

        cls.initialize()

        local_namespaces, local_module_mapping = cls.parse_configuration_files(directories=[directory])
        cls.update_namespaces(namespaces=local_namespaces, module_mapping=local_module_mapping)

        if external_directories is not None:
            external_directories = cls.resolve_external_directories(external_directories=external_directories,
                                                                    save_directory=save_directory)
            cls._MODULES = external_directories
            ext_namespaces, ext_module_mapping = cls.parse_configuration_files(directories=external_directories)
            cls.update_namespaces(namespaces=ext_namespaces, module_mapping=ext_module_mapping)

        cls.load_registrations(directory=directory)
        valid_keys, invalid_keys = cls.dag_resolution()

        return valid_keys, invalid_keys

    @classmethod
    def update_namespaces(
            cls,
            namespaces: List[str],
            module_mapping: Dict[str, List[str]]
    ):
        for key in module_mapping:
            if key in cls._MODULE_MAPPING:
                raise RuntimeWarning(f'Found duplicate namespace: {key}. Overriding existing mapping...')

        cls._EXP_NAMESPACES.extend(namespaces)
        cls._MODULE_MAPPING = {**cls._MODULE_MAPPING, **module_mapping}

    @classmethod
    def parse_configuration_files(
            cls,
            directories: List[Path]
    ) -> Tuple[List[str], Dict[str, List[str]]]:
        extractor = NamespaceExtractor()
        namespaces = []
        mapping = {}
        for directory in directories:
            for config_folder in directory.rglob('configurations'):
                for python_script in config_folder.glob('*.py'):
                    dir_namespaces = extractor.process(filename=python_script)
                    namespaces.extend(dir_namespaces)
                    mapping = {**mapping, **{namespace: directory for namespace in dir_namespaces}}

        namespaces = list(set(namespaces))
        return namespaces, mapping

    @classmethod
    def resolve_external_directories(
            cls,
            external_directories: List[Union[AnyStr, Path]],
            save_directory: Path
    ) -> List[Path]:
        resolved_directories = []
        for directory in external_directories:
            directory = Path(directory) if type(directory) != Path else directory
            if not directory.exists() or not directory.is_dir():
                try:
                    # attempt loading Git repo considering `directory` as a git URL
                    directory = git.Repo.clone_from(directory, save_directory.joinpath(directory.stem)).git_dir
                    directory = Path(directory).parent
                    logger.info(f'Detected Git repository! Cloned to {os.linesep}'
                                f'Dest: {save_directory}')
                except (git.exc.InvalidGitRepositoryError, git.exc.GitCommandError):
                    raise InvalidDirectoryException(directory=directory)
            resolved_directories.append(directory)

        return resolved_directories

    @classmethod
    def load_registrations(
            cls,
            directory: Union[AnyStr, Path],
    ):
        """
        Imports a Python's module for registration.
        In particular, the Registry looks for ``register()`` functions in each found ``__init__.py``.
        These functions are the entry points for registrations: that is, where the ``Registry`` APIs are invoked
        to issue registrations.

        Args:
            directory: path of the module
        """
        directory = Path(directory) if type(directory) != Path else directory

        if not directory.exists() or not directory.is_dir():
            raise InvalidDirectoryException(directory=directory)

        if directory in cls._EXP_MODULES:
            return

        # Add directory to PYTHONPATH
        sys.path.insert(0, directory)

        cls._EXP_MODULES.append(directory)

        cls.REGISTRY_MODE = True
        for config_folder in directory.rglob('configurations'):
            for python_script in config_folder.rglob('*.py'):
                spec = importlib.util.spec_from_file_location(name=python_script.name,
                                                              location=python_script)
                # import module and run registration methods
                if spec is not None:
                    current_keys = set(cls.REGISTRATION_METHODS.keys())
                    module = importlib.util.module_from_spec(spec=spec)
                    spec.loader.exec_module(module)
                    new_keys = set(cls.REGISTRATION_METHODS.keys()).difference(current_keys)
                    for key in new_keys:
                        key_method = cls.REGISTRATION_METHODS[key]
                        if isinstance(key_method, BufferedRegistration):
                            class_method_name = key_method.func.__qualname__.split('.')[-2]
                            method_name = key_method.func.__qualname__.split('.')[-1]
                            class_method = module.__dict__[class_method_name]
                            Registry.register_configuration(config_class=class_method,
                                                            config_constructor=getattr(class_method, method_name),
                                                            name=key_method.name,
                                                            tags=key_method.tags,
                                                            namespace=key_method.namespace,
                                                            component_class=key_method.component_class,
                                                            build_recursively=key_method.build_recursively)
                        else:
                            cls.REGISTRATION_METHODS[key]()

        cls.REGISTRY_MODE = False

    @classmethod
    def in_registry(
            cls,
            registration_key: RegistrationKey,
    ) -> bool:
        return registration_key in cls._REGISTRY

    @classmethod
    def is_namespace_covered(
            cls,
            registration_key: RegistrationKey
    ) -> bool:
        return registration_key.namespace in cls._EXP_NAMESPACES

    @classmethod
    def in_graph(
            cls,
            registration_key: Optional[Registration] = None,
            name: Optional[str] = None,
            namespace: Optional[str] = None,
            tags: cinnamon.configuration.Tags = None,
    ) -> bool:
        registration_key = RegistrationKey.parse(registration_key=registration_key,
                                                 name=name,
                                                 tags=tags,
                                                 namespace=namespace)
        return registration_key in cls._DEPENDENCY_DAG

    # DAG Resolution APIs

    @classmethod
    def check_registration_graph(
            cls
    ) -> bool:
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

    # TODO: variants of an explicit child key seems to be not considered
    # There might be a problem in how key variants are propagated
    # This might happen when different configs in a hierarchy share the same attributes -> key tags cannot discriminate
    # If this is the case, we should add discriminators when we identify tag duplicates in .from_variant() method
    @classmethod
    def dag_resolution(
            cls
    ) -> Tuple[List[RegistrationKey], List[RegistrationKey]]:
        cls.check_registration_graph()

        def _expand_node_variants(key: RegistrationKey, key_buffer: Set[RegistrationKey]):
            config_info = cls.retrieve_configuration_info(registration_key=key)
            built_config = cls.retrieve_configuration(registration_key=key)
            for child_name, child in built_config.children.items():
                child_key = child.value
                child_variants = []

                if child_key is not None:
                    child_variants = _expand_node_variants(key=child_key, key_buffer=key_buffer)
                for key_variant in child.variants:
                    if key_variant is not None:
                        child_variants.extend(_expand_node_variants(key=key_variant, key_buffer=key_buffer))

                child.variants = child.variants if child.variants is not None else []
                built_config.get(child_name).variants = list(set(child_variants + child.variants))

            variant_keys = []
            for variant_kwargs in built_config.variants:
                variant_key = key.from_variant(variant_kwargs=variant_kwargs)
                variant_config = built_config.delta_copy(**variant_kwargs)

                # Skip existing config
                if variant_config == built_config:
                    continue

                if not cls.in_graph(variant_key):
                    cls._DEPENDENCY_DAG.add_node(variant_key)
                cls._DEPENDENCY_DAG.add_edge(key, variant_key, type='variant')

                # Store variant in registry
                if not Registry.in_registry(variant_key):
                    cls.register_configuration_from_variant(config_class=config_info.config_class,
                                                            name=variant_key.name,
                                                            tags=variant_key.tags,
                                                            namespace=variant_key.namespace,
                                                            variant_kwargs=variant_kwargs,
                                                            component_class=config_info.component_class)

                variant_keys.append(variant_key)

            key_buffer.add(key)
            key_buffer.update(set(variant_keys))
            return variant_keys

        # Variants expansion doesn't change the topology of the graph -> no need for a re-check
        path_keys: Set[RegistrationKey] = set()
        for key in cls._DEPENDENCY_DAG.successors(cls._ROOT_KEY):
            _expand_node_variants(key=key, key_buffer=path_keys)

        cls.expanded = True

        # Validate paths
        valid_keys = []
        invalid_keys = []
        for key in path_keys:
            config = cls.build_configuration(registration_key=key)
            validation_result = config.validate(strict=False)
            if validation_result.passed:
                valid_keys.append(key)
            else:
                key.metadata = validation_result.error_message
                invalid_keys.append(key)

        return valid_keys, invalid_keys

    # Registration APIs

    # Component

    @classmethod
    def build_component(
            cls,
            registration_key: Optional[Registration] = None,
            name: Optional[str] = None,
            namespace: Optional[str] = None,
            tags: cinnamon.configuration.Tags = None,
            **build_args
    ) -> cinnamon.component.Component:
        """
        Builds a ``Component`` instance from its bounded ``Configuration`` via the implicit ``RegistrationKey``.

        Args:
            registration_key: the ``RegistrationKey`` used to register the ``Configuration`` class.
            name: the ``name`` field of ``RegistrationKey``
            tags: the ``tags`` field of ``RegistrationKey``
            namespace: the ``namespace`` field of ``RegistrationKey``
            build_args: TODO

        Returns:
            The built ``Component`` instance

        Raises:
            ``InvalidConfigurationTypeException``: if there's a mismatch between the ``Configuration`` class used
            during registration and the type of the built ``Configuration`` instance using the registered
            ``constructor`` method (see ``ConfigurationInfo`` arguments).

            ``NotBoundException``: if the ``Configuration`` is not bound to any ``Component``.
        """
        if not cls.expanded:
            raise NotExpandedException()

        registration_key = RegistrationKey.parse(registration_key=registration_key,
                                                 name=name,
                                                 tags=tags,
                                                 namespace=namespace)

        if not cls.in_registry(registration_key=registration_key):
            raise NotRegisteredException(registration_key=registration_key)

        registered_config_info = cls._REGISTRY[registration_key]
        config = registered_config_info.constructor()

        if registered_config_info.build_recursively:
            for child_name, child in config.children.items():
                child_key: RegistrationKey = child.value
                if child_key is not None:
                    child.value = cls.build_component(registration_key=child_key)

        if registered_config_info.component_class is None:
            raise NotBoundException(registration_key=registration_key)

        component_args = {**config.values, **build_args}
        component = registered_config_info.component_class(**component_args)

        return component

    # Configuration

    @classmethod
    def build_configuration(
            cls,
            registration_key: Optional[Registration] = None,
            name: Optional[str] = None,
            namespace: Optional[str] = None,
            tags: cinnamon.configuration.Tags = None,
    ) -> cinnamon.configuration.Configuration:
        """
            Retrieves a configuration instance given its implicit registration key.

        Args:
            registration_key: key used to register the configuration
            name: the ``name`` field of ``RegistrationKey``
            namespace: the ``namespace`` field of ``RegistrationKey``
            tags: the ``tags`` field of ``RegistrationKey``

        Returns:
            The built configuration
        """
        if not cls.expanded:
            raise NotExpandedException()

        registration_key = RegistrationKey.parse(registration_key=registration_key,
                                                 name=name,
                                                 tags=tags,
                                                 namespace=namespace)

        if not cls.in_registry(registration_key=registration_key):
            raise NotRegisteredException(registration_key=registration_key)

        config_info = cls._REGISTRY[registration_key]
        config = config_info.constructor()

        for child_name, child in config.children.items():
            child_key: RegistrationKey = child.value
            if child_key is not None:
                child.value = cls.build_configuration(registration_key=child_key)

        return config

    @classmethod
    def register_configuration(
            cls,
            config_class: Type[cinnamon.configuration.Configuration],
            name: str,
            namespace: str,
            tags: cinnamon.configuration.Tags = None,
            config_constructor: Optional[Constructor] = None,
            component_class: Optional[Type[cinnamon.component.Component]] = None,
            build_recursively: bool = True
    ):
        """
        Registers a ``Configuration`` in the ``Registry`` via explicit ``RegistrationKey``.
        In particular, a ``ConfigurationInfo`` wrapper is stored in the ``Registry``.

        Args:
            config_class: the class of the ``Configuration``
            name: the ``name`` field of ``RegistrationKey``
            namespace: the ``namespace`` field of ``RegistrationKey``
            tags: the ``tags`` field of ``RegistrationKey``
            config_constructor: the constructor method to build the ``Configuration`` instance from its class
            component_class: TODO
            build_recursively: TODO

        Returns:
            The built ``RegistrationKey`` instance that can be used to retrieve the registered ``ConfigurationInfo``.

        Raises:
            ``AlreadyRegisteredException``: if the ``RegistrationKey`` is already used
        """
        if cls.expanded:
            raise AlreadyExpandedException()

        registration_key = RegistrationKey(name=name,
                                           tags=tags,
                                           namespace=namespace)

        # Check if already registered
        if cls.in_registry(registration_key=registration_key):
            raise AlreadyRegisteredException(registration_key=registration_key)

        # Store configuration in registry
        config_constructor = config_constructor if config_constructor is not None else config_class.default
        cls._REGISTRY[registration_key] = ConfigurationInfo(config_class=config_class,
                                                            constructor=config_constructor,
                                                            component_class=component_class,
                                                            build_recursively=build_recursively)

        # Add to dependency graph
        cls._DEPENDENCY_DAG.add_node(registration_key)
        if not len(cls._DEPENDENCY_DAG.in_edges(registration_key)):
            cls._DEPENDENCY_DAG.add_edge(cls._ROOT_KEY, registration_key, type='child')

        built_config = config_constructor()

        # include children
        for child_name, child in built_config.children.items():
            child_key: RegistrationKey = child.value
            if child_key is None:
                if child.variants is None:
                    continue

                for variant in child.variants:
                    if not cls.in_graph(variant):
                        cls._DEPENDENCY_DAG.add_node(variant)
                    cls._DEPENDENCY_DAG.add_edge(registration_key, variant, type='child')
                    if variant.namespace != namespace:
                        if not cls.is_namespace_covered(variant):
                            raise NamespaceNotFoundException(registration_key=registration_key,
                                                             namespaces=cls._EXP_NAMESPACES)
                        cls.load_registrations(directory=cls._MODULE_MAPPING[variant.namespace])

                continue

            if not cls.in_graph(child_key):
                cls._DEPENDENCY_DAG.add_node(child_key)
            cls._DEPENDENCY_DAG.add_edge(registration_key, child_key, type='child')
            if child_key.namespace != namespace:
                if not cls.is_namespace_covered(child_key):
                    raise NamespaceNotFoundException(registration_key=registration_key, namespaces=cls._EXP_NAMESPACES)
                cls.load_registrations(directory=cls._MODULE_MAPPING[child_key.namespace])

        return registration_key

    @classmethod
    def register_configuration_from_variant(
            cls,
            config_class: Type[cinnamon.configuration.Configuration],
            name: str,
            namespace: str,
            variant_kwargs: Dict[str, Any],
            tags: cinnamon.configuration.Tags = None,
            config_constructor: Optional[Constructor] = None,
            component_class: Optional[Type[cinnamon.component.Component]] = None,
            build_recursively: bool = True
    ):
        config_constructor = config_constructor if config_constructor is not None else config_class.default
        return cls.register_configuration(config_class=config_class,
                                          name=name,
                                          namespace=namespace,
                                          tags=tags,
                                          config_constructor=lambda: config_constructor().delta_copy(**variant_kwargs),
                                          component_class=component_class,
                                          build_recursively=build_recursively)

    @classmethod
    def retrieve_configuration(
            cls,
            registration_key: Optional[Registration] = None,
            name: Optional[str] = None,
            namespace: Optional[str] = None,
            tags: cinnamon.configuration.Tags = None,
    ) -> cinnamon.configuration.Configuration:
        """
            Retrieves a configuration instance given its implicit registration key.

        Args:
            registration_key: key used to register the configuration
            name: the ``name`` field of ``RegistrationKey``
            namespace: the ``namespace`` field of ``RegistrationKey``
            tags: the ``tags`` field of ``RegistrationKey``

        Returns:
            The built configuration
        """

        registration_key = RegistrationKey.parse(registration_key=registration_key,
                                                 name=name,
                                                 tags=tags,
                                                 namespace=namespace)

        if not cls.in_registry(registration_key=registration_key):
            raise NotRegisteredException(registration_key=registration_key)

        config_info = cls._REGISTRY[registration_key]
        config = config_info.constructor()
        return config

    @classmethod
    def retrieve_configuration_info(
            cls,
            registration_key: Optional[RegistrationKey] = None,
            name: Optional[str] = None,
            namespace: Optional[str] = None,
            tags: cinnamon.configuration.Tags = None,
    ) -> ConfigurationInfo:
        registration_key = RegistrationKey.parse(registration_key=registration_key,
                                                 name=name,
                                                 tags=tags,
                                                 namespace=namespace)

        if cls.in_registry(registration_key=registration_key):
            return cls._REGISTRY[registration_key]
        else:
            raise NotRegisteredException(registration_key=registration_key)

    # Views

    @classmethod
    def show_registrations(
            cls,
            keys: List[RegistrationKey]
    ):
        for key in keys:
            logger.info(key)
