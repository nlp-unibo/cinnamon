from __future__ import annotations

import ast
import importlib.util
import itertools
import sys
from collections.abc import ItemsView
from dataclasses import dataclass
from logging import getLogger
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    List,
    Set,
    Tuple,
    TypeVar,
    Union,
)

import networkx as nx
import pydantic
from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema

import cinnamon.configuration
from cinnamon.utility.configuration import batched
from cinnamon.utility.dependencies import (
    DependencyShape,
    dependency_members,
    iter_dependency_keys,
    map_dependency_keys,
)
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
from cinnamon.utility.suggestions import suggest_keys

logger = getLogger(__name__)

Constructor = Callable[[], "cinnamon.configuration.Configuration"]
T = TypeVar("T")

__all__ = ["RegistrationKey", "register", "register_method", "Registry", "Registration"]


class RegistrationKey(Generic[T]):
    """
    Compound key used for registration.
    """

    # Declared for type checkers and IDEs. These are assigned through
    # ``object.__setattr__`` in ``__init__`` to bypass the immutability guard in
    # ``__setattr__``; without the annotations they are invisible to static
    # analysis even though every caller reads them.
    name: str
    namespace: str
    tags: frozenset[str]

    #: Free-form documentation for the key.
    description: str | None
    #: Why a key was rejected, filled in by resolution for invalid keys.
    metadata: str | None
    #: Internal markers such as ``__runnable``; not part of the key's identity.
    special_tags: set[str]

    _IMMUTABLE = frozenset({"name", "namespace", "tags"})

    KEY_VALUE_SEPARATOR: str = "="
    ATTRIBUTE_SEPARATOR: str = "--"
    HIERARCHY_SEPARATOR: str = "."
    MAX_TAGS_PER_LINE: int = 6

    def __init__(
        self,
        name: str,
        namespace: str | None = None,
        tags: Tags = None,
        description: str | None = None,
        metadata: str | None = None,
        special_tags: Tags = None,
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

        object.__setattr__(self, "name", name)
        object.__setattr__(
            self, "namespace", namespace if namespace is not None else "default"
        )
        object.__setattr__(
            self, "tags", frozenset(tags) if tags is not None else frozenset()
        )

        self.description = description
        self.metadata = metadata
        # Copied, not aliased: ``from_variant`` passes the parent's set straight
        # through, so sharing the object would make every key derived from a
        # common ancestor mutate together.
        self.special_tags = set(special_tags) if special_tags is not None else set()

        self._hash = hash(str(self))

    def __setattr__(self, attr: str, value: Any) -> None:
        if attr in RegistrationKey._IMMUTABLE:
            raise AttributeError(
                f"RegistrationKey.{attr!r} is immutable and cannot be reassigned."
            )
        super().__setattr__(attr, value)

    @classmethod
    def _validate(cls, value: Any) -> "RegistrationKey[Any]":
        """Accept a key as-is, or parse one from its canonical string form.

        Anything else raises ``ValueError`` rather than being coerced through
        ``str()``. That matters inside a union such as
        ``RegistrationKey | list[RegistrationKey]``: pydantic only falls through
        to the next member when this one reports a validation failure, so a
        blanket ``str()`` coercion would swallow the list and then die parsing
        its repr.
        """
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            return cls.from_string(value)
        raise ValueError(
            f"Cannot build a {cls.__name__} from {type(value).__name__}; "
            f"expected a {cls.__name__} or its string form."
        )

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ):
        return core_schema.no_info_plain_validator_function(
            function=cls._validate,
            serialization=core_schema.plain_serializer_function_ser_schema(
                function=str, return_schema=core_schema.str_schema(), when_used="json"
            ),
        )

    def __hash__(self) -> int:
        return self._hash

    def __str__(self) -> str:
        to_return = [f"name{self.KEY_VALUE_SEPARATOR}{self.name}"]

        if self.tags:
            tags = sorted(self.tags)
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

    def check_name(self, name: str) -> bool:
        return self.name == name

    def check_tags(self, tags: Tags) -> bool:
        # ``self.tags`` is normalised to a frozenset in __init__ and is never
        # None, so only the incoming value needs guarding.
        return tags is not None and self.tags == tags

    def check_namespace(self, namespace: str) -> bool:
        # ``self.namespace`` defaults to "default" in __init__ and is never None.
        return namespace is not None and self.namespace == namespace

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
        self,
        variant_kwargs: Dict[str, Any],
        variant_indexes: Dict[str, int] | None = None,
    ) -> RegistrationKey[T]:
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

        return RegistrationKey[T](
            name=self.name,
            tags=self.tags.union(set(variant_tags)),
            namespace=self.namespace,
            special_tags=self.special_tags,
            description=self.description,
            metadata=self.metadata,
        )

    def from_tags_simplification(self, tags: Tags) -> RegistrationKey[T]:
        """
        Builds a new ``RegistrationKey`` from current instance
        by removing provided tags.

        Args:
            tags: a Tag set containing tags to remove

        Returns:
            A ``RegistrationKey`` instance that is the same as the current instance
            but with ``tags`` removed.

        """
        tags = tags or set()
        remaining_tags = self.tags.difference(tags)
        return RegistrationKey[T](
            name=self.name,
            tags=remaining_tags,
            namespace=self.namespace,
            description=self.description,
            special_tags=self.special_tags,
            metadata=self.metadata,
        )

    @classmethod
    def from_string(cls, string_format: str) -> RegistrationKey[Any]:
        """
        Parses a ``RegistrationKey`` instance from its string format.

        Args:
            string_format: the string format of a ``RegistrationKey`` instance.

        Returns:
            The corresponding parsed ``RegistrationKey`` instance
        """

        registration_attributes = string_format.split(cls.ATTRIBUTE_SEPARATOR)
        registration_dict: Dict[str, Any] = {}
        for registration_attribute in registration_attributes:
            try:
                key, raw_value = registration_attribute.split(
                    cls.KEY_VALUE_SEPARATOR, 1
                )
                registration_dict[key] = (
                    set(ast.literal_eval(raw_value)) if key == "tags" else raw_value
                )
            except ValueError as e:
                logger.exception(
                    f"Failed parsing registration key from string.. "
                    f"Got: {string_format}"
                )
                raise e

        return RegistrationKey[Any](**registration_dict)

    @classmethod
    def parse(
        cls,
        registration_key: Registration | None = None,
        name: str | None = None,
        namespace: str | None = None,
        tags: Tags = None,
    ) -> RegistrationKey[Any]:
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

            registration_key = RegistrationKey[Any](
                name=name,
                tags=set(tags) if tags is not None else tags,
                namespace=namespace,
            )

        return registration_key

    def match(self, key: RegistrationKey, tags: Tags) -> bool:
        return self.tags.intersection(key.tags) == tags

    def to_pretty_string(self) -> str:
        # batched() takes a chunk *size*, so pass the per-line budget directly;
        # handing it the chunk count produced MAX_TAGS_PER_LINE lines of
        # len(tags) / MAX_TAGS_PER_LINE tags each -- the transpose of the intent.
        splits = batched(sorted(self.tags), RegistrationKey.MAX_TAGS_PER_LINE)
        tags = "\n                      ".join(", ".join(item) for item in splits)

        return (
            f"[\n"
            f"                name: {self.name}\n"
            f"                tags: {tags}\n"
            f"                namespace: {self.namespace}\n"
            f"            ]\n        "
        )


class BufferedRegistration:
    def __init__(
        self,
        func: Callable,
        name: str,
        namespace: str,
        tags: Tags = None,
        component: str | None = None,
        run_method: str | None = None,
    ):
        self.func = func
        self.name = name
        self.namespace = namespace
        self.tags = tags
        self.component = component
        self.run_method = run_method


#: A registration key, or its canonical string form. Defined after the class so
#: the alias holds the real type: a forward reference here cannot be resolved
#: from other modules' namespaces, which broke the generated API docs.
Registration = Union[RegistrationKey, str]


def register_method(
    name: str,
    namespace: str,
    tags: Tags = None,
    component: str | None = None,
    run_method: str | None = None,
) -> Callable:
    def register_wrapper(func):
        key = str(RegistrationKey[Any](name=name, tags=tags, namespace=namespace))
        if (
            hasattr(Registry, "REGISTRATION_CONTEXT")
            and Registry.REGISTRATION_CONTEXT.is_registering
            and key not in Registry.REGISTRATION_METHODS
        ):
            Registry.REGISTRATION_METHODS[key] = BufferedRegistration(
                func=func,
                name=name,
                tags=tags,
                namespace=namespace,
                component=component,
                run_method=run_method,
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
    component: str | None = None
    run_method: str | None = None


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

    _REGISTRY: Dict[RegistrationKey[Any], ConfigurationInfo]

    _ROOT_KEY = RegistrationKey[Any](name="root", namespace="root")
    _DEPENDENCY_DAG: nx.DiGraph

    expanded: bool = False

    _MODULES: List[Union[str, Path]]
    _EXP_MODULES: Set[Path]
    _MODULE_MAPPING: Dict[str, Path]
    _EXP_NAMESPACES: List[str]

    REGISTRATION_METHODS: Dict[str, Callable | BufferedRegistration]
    REGISTRATION_CONTEXT: RegistrationContext

    @classmethod
    def initialize(cls):
        """Reset registry to empty state."""
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
    def load(
        cls,
        directory: Union[Path, str],
        external_directories: List[Union[str, Path]] | None = None,
    ) -> None:
        """
        Populate the registry and the dependency DAG, without resolving them.

        This is the first half of ``build``: after it returns, every
        registration has been executed and every referenced key is a node in the
        DAG -- including keys that were referenced but never registered. That
        makes it the point at which the whole set of broken references can be
        inspected at once, which ``dag_resolution`` cannot do because it stops
        at the first one.

        Args:
            directory: the main directory of the project containing configurations.
            external_directories: external directories containing configurations.
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

    @classmethod
    @time_it
    def build(
        cls,
        directory: Union[Path, str],
        external_directories: List[Union[str, Path]] | None = None,
    ) -> Tuple[Set[RegistrationKey[Any]], Set[RegistrationKey[Any]]]:
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
            RuntimeWarning: if duplicate namespaces are found.
            InvalidDirectoryException: if one of the provided directories does
                not exist or is not a directory.
            AlreadyExpandedException: if the dependency DAG has been expanded.
            NotADAGException: if the dependency DAG is not a DAG.
            DisconnectedGraphException: if the dependency DAG contains
                disconnected nodes. This should never happen through the
                cinnamon APIs, only through manual edits to the graph.
        """

        cls.load(directory=directory, external_directories=external_directories)
        valid_keys, invalid_keys = cls.dag_resolution()

        cls._REGISTRY = {
            key: value for key, value in cls._REGISTRY.items() if key in valid_keys
        }

        return valid_keys, invalid_keys

    @classmethod
    @time_it
    def update_namespaces(cls, namespaces: List[str], module_mapping: Dict[str, Path]):
        """
        Merge namespaces into registry mappings.

        Raises:
            ``RuntimeWarning``: if a namespace is already mapped to a directory.
                Two directories claiming one namespace makes resolution ambiguous,
             so the merge is refused rather than silently resolved.
        """
        for key in module_mapping:
            if key in cls._MODULE_MAPPING:
                raise RuntimeWarning(
                    f"Found duplicate namespace: {key}. It is already mapped to "
                    f"{cls._MODULE_MAPPING[key]}, so {module_mapping[key]} cannot "
                    f"also claim it. Rename one of the two namespaces."
                )

        cls._EXP_NAMESPACES.extend(namespaces)
        cls._MODULE_MAPPING.update(module_mapping)

    @classmethod
    @time_it
    def parse_configuration_files(
        cls, directories: List[Path]
    ) -> Tuple[List[str], Dict[str, Path]]:
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
        namespaces: List[str] = []
        mapping: Dict[str, Path] = {}
        for directory in directories:
            for config_folder in directory.rglob(Registry._CONFIGURATION_FOLDER):
                for python_script in config_folder.glob("*.py"):
                    dir_namespaces = extractor.process(filename=python_script)
                    namespaces.extend(dir_namespaces)
                    mapping.update(
                        {namespace: directory for namespace in dir_namespaces}
                    )

        namespaces = list(set(namespaces))
        return namespaces, mapping

    @classmethod
    @time_it
    def resolve_external_directories(
        cls,
        external_directories: List[Union[str, Path]],
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
        directory: Union[str, Path],
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

                # unreachable via rglob("*.py"); defensive guard kept for
                # non-standard loaders and excluded from coverage.
                if spec is None or spec.loader is None:  # pragma: no cover
                    logger.error(f"Could not load {python_script}.")
                    raise RuntimeError(f"Could not load {python_script}.")

                # import module and run registration methods
                current_keys = set(cls.REGISTRATION_METHODS.keys())

                try:
                    module = importlib.util.module_from_spec(spec=spec)
                    spec.loader.exec_module(module)
                except Exception as e:
                    logger.error(f"Failed to execute module {python_script.name}. {e}")
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
                        )
                    else:
                        key_method()

    @classmethod
    def in_registry(
        cls,
        registration_key: RegistrationKey[T],
    ) -> bool:
        """Return True if key is stored."""
        return registration_key in cls._REGISTRY

    @classmethod
    def is_namespace_covered(cls, registration_key: RegistrationKey[T]) -> bool:
        """Return True if namespace covered."""
        return registration_key.namespace in cls._EXP_NAMESPACES

    @classmethod
    def in_graph(
        cls,
        registration_key: Registration | None = None,
        name: str | None = None,
        namespace: str | None = None,
        tags: Tags = None,
    ) -> bool:
        """Return True if key in dependency DAG."""
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
            AlreadyExpandedException: if the dependency DAG has been expanded.
            NotADAGException: if the dependency DAG is not a DAG.
            DisconnectedGraphException: if the dependency DAG contains
                disconnected nodes. This should never happen through the
                cinnamon APIs, only through manual edits to the graph.
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
    def dag_resolution(
        cls,
    ) -> Tuple[Set[RegistrationKey[Any]], Set[RegistrationKey[Any]]]:
        """
        Expands and resolves every dependency in the registration DAG.

        Keys are expanded **children first**, in reverse topological order.
        ``expand_configuration`` recurses into a key's dependencies, so reaching
        a parent before its children makes the recursion as deep as the longest
        chain in the project -- and Python's stack limit then caps that chain at
        roughly 490 links.

        That cap used to depend on the order modules happened to register in: the
        same graph resolved when children were registered first (each expansion
        finding its children already done, so nesting stayed shallow) and hit
        ``RecursionError`` when parents came first. Taking the order from the
        graph rather than from registration removes both the depth limit and the
        dependence on something no user controls.

        Returns:
            valid_keys: the set of valid registration keys
            invalid_keys:the set of invalid registration keys
        """

        cls.check_registration_graph()

        # Variants expansion doesn't change the topology of the graph
        valid_key_buffer: Set[RegistrationKey[Any]] = set()
        invalid_key_buffer: Set[RegistrationKey[Any]] = set()
        logger.info(f"Resolving {len(cls._REGISTRY)} configurations...")

        # Materialised before expanding: expansion adds variant nodes to the
        # graph, and topological_sort is a generator over a live view.
        order = list(nx.topological_sort(cls._DEPENDENCY_DAG))
        for key in reversed(order):
            if key == cls._ROOT_KEY:
                continue
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
        key: RegistrationKey[T],
        valid_key_buffer: Set[RegistrationKey[T]] | None = None,
        invalid_key_buffer: Set[RegistrationKey[T]] | None = None,
    ) -> Set[RegistrationKey[Any]]:
        """Recursively expand configuration and dependencies."""
        valid_key_buffer = valid_key_buffer if valid_key_buffer is not None else set()
        invalid_key_buffer = (
            invalid_key_buffer if invalid_key_buffer is not None else set()
        )

        config_info = cls.retrieve_configuration_info(registration_key=key)
        config = config_info.config

        # Already expanded: rebuild what the fresh path below would have
        # returned, which is this key plus the variant keys derived from it.
        #
        # Only "variant" edges count. Taking every out-edge also swept in the
        # "child" edges to the key's dependencies, so a caller received another
        # configuration's key as though it were an alternative to this one, and
        # generated a spurious parent variant from it. The two paths disagreed
        # silently for as long as parents happened to be expanded before their
        # children.
        if config.expanded:
            return {
                child
                for _, child, edge_type in cls._DEPENDENCY_DAG.out_edges(
                    key, data="type"
                )
                if edge_type == "variant"
            } | {key}

        keys = set()

        # dependencies
        for dependency_name, field in config.fields.items():
            if dependency_name not in config.dependencies:
                continue

            dependency = config.dependencies[dependency_name]
            shape = config.dependency_shape(field_name=dependency_name, field=field)
            declared_variants = config.meta[dependency_name].variants

            def expand(dependency_key: RegistrationKey[Any]) -> Set[Any]:
                return Registry.expand_configuration(
                    key=dependency_key,
                    valid_key_buffer=valid_key_buffer,
                    invalid_key_buffer=invalid_key_buffer,
                )

            if shape is not DependencyShape.SCALAR:
                # Container dependency. Every member is expanded so its own
                # variants are registered and validated, but the field's variant
                # list is left alone: a container field varies as a whole
                # container, so injecting bare member keys here would make
                # ``config.variants`` offer a single key where a list belongs.
                for candidate in [dependency, *declared_variants]:
                    for member in iter_dependency_keys(candidate):
                        expand(member)
                continue

            # Scalar dependency. When the child expands to more than itself, the
            # extra keys become variants of this field, so the parent gains one
            # variant per child variant.
            dependency_variants: Set[Any] = set()
            if dependency is not None:
                dependency_variants |= expand(dependency)
                dependency_variants.discard(dependency)

            for key_variant in declared_variants:
                for member in iter_dependency_keys(key_variant):
                    dependency_variants |= expand(member)

            config.meta[dependency_name].variants = list(dependency_variants)

        # variants
        for variant_info in config.variants:
            variant_key = key.from_variant(
                variant_kwargs=variant_info["values"],
                variant_indexes=variant_info["indexes"],
            )

            if not cls.in_graph(variant_key):
                cls._DEPENDENCY_DAG.add_node(variant_key)
            cls._DEPENDENCY_DAG.add_edge(key, variant_key, type="variant")

            try:
                variant_config = config.model_copy(
                    update=variant_info["values"], deep=True
                )
            except pydantic.ValidationError as validation_error:
                variant_key.metadata = repr(validation_error)
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
                )

            resolved_config = Registry.resolve_configuration(
                config=variant_config.model_copy(deep=True)
            )
            validation_result = resolved_config.validate_conditions(strict=False)

            if validation_result.passed:
                keys.add(variant_key)
                valid_key_buffer.add(variant_key)
            else:
                variant_key.metadata = validation_result.stack_trace
                invalid_key_buffer.add(variant_key)

        resolved_config = Registry.resolve_configuration(
            config=config.model_copy(deep=True)
        )
        validation_result = resolved_config.validate_conditions(strict=False)

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
    def from_key(
        cls,
        registration_key: RegistrationKey[T],
        **build_args,
    ) -> T:
        """Build component from key."""
        instance: T = Registry.instantiate(
            registration_key=registration_key, **build_args
        )
        return instance

    @classmethod
    def from_keys(cls, dependency: Any, **build_args) -> Any:
        """
        Build every component in a dependency, keeping the shape it came in.

        A component receives its dependencies as keys, so that it decides when
        each child is built. When the dependency is a container that usually
        means a comprehension per field::

            self.losses = [Registry.from_key(key) for key in losses]
            self.metrics = {name: Registry.from_key(key)
                            for name, key in metrics.items()}

        which says nothing except "build these". ``from_keys`` says it once::

            self.losses = Registry.from_keys(losses)     # list  -> list, in order
            self.metrics = Registry.from_keys(metrics)   # dict  -> dict, same labels

        A single key builds a single component, so a field typed
        ``RegistrationKey | list[RegistrationKey]`` needs no branch. ``None``
        returns ``None``, which is what an unset optional dependency should do.
        Anything that is not a key is passed through untouched.

        ``build_args`` are forwarded to every component built.

        This builds **eagerly**. Keep the loop when a child should only be built
        under some condition -- the laziness is the reason components are handed
        keys rather than instances.
        """
        return map_dependency_keys(
            dependency, lambda key: cls.from_key(key, **build_args)
        )

    @classmethod
    def instantiate(
        cls,
        registration_key: Registration | None = None,
        name: str | None = None,
        namespace: str | None = None,
        tags: Tags = None,
        expected_type: type | None = None,
        **build_args,
    ) -> Any:
        """
        Builds a ``Component`` instance from its bounded ``Configuration``
        via the implicit ``RegistrationKey``.

        Args:
            registration_key: the ``RegistrationKey`` used to register the
                ``Configuration`` class.
            name: the ``name`` attribute of ``RegistrationKey``
            tags: the ``tags`` attribute of ``RegistrationKey``
            namespace: the ``namespace`` attribute of ``RegistrationKey``
            expected_type: type of the component to be cast
            build_args: additional custom component constructor args

        Returns:
            The built component instance

        Raises:
            ``InvalidConfigurationTypeException``: if there's a mismatch between
                the ``Configuration`` class used during registration and the type of the
              built ``Configuration`` instance using the registered
            ``constructor`` method (see ``ConfigurationInfo`` arguments).

            ``NotBoundException``: if the ``Configuration`` is not bound to
                any component.
        """
        if not cls.expanded:
            raise NotExpandedException()

        registration_key = RegistrationKey.parse(
            registration_key=registration_key, name=name, tags=tags, namespace=namespace
        )

        if not cls.in_registry(registration_key=registration_key):
            raise NotRegisteredException(
                registration_key=registration_key,
                suggestions=suggest_keys(registration_key, cls._REGISTRY),
            )

        config_info: ConfigurationInfo = cls._REGISTRY[registration_key]
        config = config_info.config

        if config_info.component is None:
            raise NotBoundException(registration_key=registration_key)

        component_args = {**config.values, **build_args}
        component_class = import_class_from_string(config_info.component)

        if expected_type is not None and not issubclass(component_class, expected_type):
            raise TypeError(
                f"'{config_info.component}' resolves to {component_class.__name__}, "
                f"which is not a subclass of {expected_type.__name__}."
            )

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
        component: str | None = None,
        run_method: str | None = None,
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

        registration_key = RegistrationKey[Any](
            name=name, tags=tags, namespace=namespace
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
            # A dependency field holds a key, a list of them, or a dict of
            # them -- and each declared variant is a whole value of that same
            # shape. Every key reachable from any of them becomes a child edge.
            declared_variants = config.meta[dependency_name].variants

            # The field's own value has to reference registrations. A nested
            # Configuration instance, or any other stray value, cannot become a
            # DAG edge -- say so here rather than dropping it silently.
            for member in dependency_members(dependency):
                if not isinstance(member, RegistrationKey):
                    raise TypeError(
                        f"Dependency '{dependency_name}' holds "
                        f"{type(member).__name__!r} where a RegistrationKey was "
                        f"expected."
                    )

            # Declared variants stay lenient: Param(variants=[...]) may mix
            # keys with plain sentinel values, and only the keys are nodes.
            for dep in itertools.chain.from_iterable(
                iter_dependency_keys(candidate)
                for candidate in [dependency, *declared_variants]
            ):
                if not cls.in_graph(dep):
                    cls._DEPENDENCY_DAG.add_node(dep)

                cls._DEPENDENCY_DAG.add_edge(registration_key, dep, type="child")

                if dep.namespace != namespace:
                    if not cls.is_namespace_covered(dep):
                        raise NamespaceNotFoundException(
                            registration_key=registration_key,
                            namespaces=cls._EXP_NAMESPACES,
                            missing_namespace=dep.namespace,
                        )
                    cls.load_registrations(directory=cls._MODULE_MAPPING[dep.namespace])

        return registration_key

    @classmethod
    def resolve_configuration(
        cls, config: cinnamon.configuration.Configuration
    ) -> cinnamon.configuration.Configuration:
        """
        Replace every dependency key with the ``Configuration`` it names.

        Container shapes survive: a ``list[RegistrationKey]`` field becomes a
        list of configurations in the same order, a ``dict[str, RegistrationKey]``
        keeps its labels. Members that are already resolved are left alone, so
        the call is idempotent.

        This runs on throwaway copies during validation. The *registered*
        configuration keeps its raw keys, which is what components receive --
        they call ``Registry.from_key`` on them to build their own children.
        """

        def resolve(dependency_key: RegistrationKey[Any]) -> Any:
            return Registry.retrieve_configuration(registration_key=dependency_key)

        for dependency_name, dependency in config.dependencies.items():
            resolved = map_dependency_keys(dependency, resolve)
            if resolved is not dependency:
                setattr(config, dependency_name, resolved)

            config.meta[dependency_name].variants = [
                map_dependency_keys(variant_value, resolve)
                for variant_value in config.meta[dependency_name].variants
            ]

        return config

    @classmethod
    def _retrieve(
        cls,
        registration_key: Registration | None = None,
        name: str | None = None,
        namespace: str | None = None,
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

        parsed_key: RegistrationKey = RegistrationKey.parse(
            registration_key=registration_key, name=name, tags=tags, namespace=namespace
        )

        if not cls.in_registry(registration_key=parsed_key):
            raise NotRegisteredException(
                registration_key=parsed_key,
                suggestions=suggest_keys(parsed_key, cls._REGISTRY),
            )

        return cls._REGISTRY[parsed_key]

    @classmethod
    def retrieve_configuration(
        cls,
        registration_key: Registration | None = None,
        name: str | None = None,
        namespace: str | None = None,
        tags: Tags = None,
    ) -> cinnamon.configuration.Configuration:
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
        registration_key: Registration | None = None,
        name: str | None = None,
        namespace: str | None = None,
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
            The ConfigurationInfo stored under the parsed key.
        """
        return cls._retrieve(
            registration_key=registration_key, name=name, namespace=namespace, tags=tags
        )

    @classmethod
    def registered_items(
        cls,
    ) -> "ItemsView[RegistrationKey[Any], ConfigurationInfo]":
        """
        Return a read-only view over ``(key, ConfigurationInfo)`` pairs.

        Public counterpart to ``_REGISTRY`` for consumers that need to walk the
        whole registry (the static analyzer, reporting tools) without depending
        on the internal container.
        """
        return cls._REGISTRY.items()

    @classmethod
    def unresolved_keys(cls) -> Set["RegistrationKey[Any]"]:
        """
        Keys that something depends on but nothing registered.

        Meaningful between ``load`` and ``dag_resolution``: registration adds a
        node for every referenced key, so anything in the graph without a
        registry entry is a broken reference. After a successful ``build`` the
        set is empty, since resolution would have failed.
        """
        nodes = set(cls._DEPENDENCY_DAG.nodes) - {cls._ROOT_KEY}
        return nodes - set(cls._REGISTRY)

    @classmethod
    def retrieve_keys(
        cls,
        names: Union[List[str], str] | None = None,
        namespaces: Union[List[str], str] | None = None,
        tags: Tags = None,
        special_tags: Tags = None,
        keys: List[RegistrationKey[T]] | None = None,
    ) -> List[RegistrationKey[Any]]:
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
            Matching RegistrationKey instances.
        """

        candidates = keys if keys is not None else list(cls._REGISTRY.keys())

        return [
            key
            for key in candidates
            if match_name(name=key.name, names=names)
            and match_namespace(namespace=key.namespace, namespaces=namespaces)
            and match_tags(a_tags=key.tags, b_tags=tags)
            and match_tags(a_tags=key.special_tags, b_tags=special_tags)
        ]

    @classmethod
    def retrieve_runnable_keys(cls) -> List[RegistrationKey[Any]]:
        """Return keys marked runnable (run_method set)."""
        return cls.retrieve_keys(special_tags={"__runnable"})
