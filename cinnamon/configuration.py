from __future__ import annotations

import logging
import os
from copy import deepcopy
from dataclasses import dataclass
from functools import partial
from typing import Dict, Any, Callable, Optional, TypeVar, Sized, List, Set, Union, Type

from pandas import json_normalize
from typeguard import check_type, TypeCheckError

import cinnamon.component
import cinnamon.registry
from cinnamon.utility.configuration import get_dict_values_combinations

C = TypeVar('C', bound='Configuration')
P = TypeVar('P', bound='Param')

Constructor = Callable[[Any], C]
Tags = Optional[Set[str]]

__all__ = [
    'Configuration',
    'ValidationFailureException',
    'ValidationResult',
    'C',
    'P',
    'Tags',
    'Param'
]

logger = logging.getLogger(__name__)


class OutOfRangeParameterValueException(Exception):

    def __init__(self, value):
        super().__init__(f'Parameter value {value} not in allowed range')


class InconsistentTypeException(Exception):

    def __init__(self, expected_type, given_type):
        super().__init__(f'Expected parameter value with type {expected_type} but got {given_type}')


class AlreadyExistingParameterException(Exception):

    def __init__(
            self,
            param: Param
    ):
        super().__init__(f'Parameter {param.name} already exists! {os.linesep}'
                         f'Parameter: {param}')


class NonExistingParameterException(Exception):

    def __init__(
            self,
            name: str
    ):
        super().__init__(f'Cannot find any parameter with name {name}.')


@dataclass
class ValidationResult:
    """
    Utility dataclass to store conditions evaluation result (see ``Configuration.validate()``).

    Args:
        passed: True if all conditions are True
        error_message: a string message reporting which condition failed during the evaluation process.
    """

    passed: bool
    source: str
    error_message: Optional[str] = None


class ValidationFailureException(Exception):

    def __init__(
            self,
            validation_result: ValidationResult
    ):
        super().__init__(f'Source: {validation_result.source}{os.linesep}'
                         f'The validation process has failed!{os.linesep}'
                         f'Passed: {validation_result.passed}{os.linesep}'
                         f'Error message: {validation_result.error_message}')


def is_required_cond(
        config: Configuration,
        name: str
) -> bool:
    return config.get(name).value is not None


def value_typecheck_cond(
        config: Configuration,
        name: str,
        type_hint: Type
) -> bool:
    try:
        check_type(value=config.get(name).value, expected_type=type_hint)
        return True
    except TypeCheckError:
        return False


def allowed_range_cond(
        config: Configuration,
        name: str,
) -> bool:
    found_param = config.get(name)

    if found_param.value is not None and not found_param.allowed_range(found_param.value):
        return False
    return True


def valid_variants_cond(
        config: Configuration,
        name: str
):
    return len(config.get(name).variants) > 0


class Param:
    """
    A generic attribute wrapper that allows
    - type annotation
    - textual description metadata
    - tags metadata for categorization and general-purpose retrieval
    """

    def __init__(
            self,
            name: str,
            value: Any = None,
            type_hint: Optional[Type] = None,
            description: Optional[str] = None,
            tags: Tags = None,
            allowed_range: Optional[Callable[[Any], bool]] = None,
            is_required: bool = True,
            variants: Optional[List] = None,
    ):
        """
        The ``Parameter`` constructor

        Args:
            name: unique identifier of the ``Field`` instance
            value: the wrapped value of the ``Field`` instance
            type_hint: type annotation concerning ``value``
            description: a string description of the ``Field`` for readability purposes
            tags: a set of string tags to mark the ``Field`` instance with metadata.
            allowed_range: allowed range of values for ``value``
            is_required: if True, ``value`` cannot be None
            variants: set of variant values of ``value`` of interest
        """

        self.name = name
        self.value = value
        self.type_hint = type_hint
        self.description = description
        self.tags = set(tags) if tags is not None else set()
        self.allowed_range = allowed_range
        self.is_required = is_required
        self.variants = variants if variants is not None else []

    @property
    def is_child(
            self
    ):
        return (type(self.value) == cinnamon.registry.RegistrationKey
                or self.type_hint == cinnamon.registry.RegistrationKey
                or isinstance(self.value, Configuration)
                or isinstance(self.value, cinnamon.component.Component))

    def short_repr(
            self
    ) -> str:
        return f'{self.value}'

    def long_repr(
            self
    ) -> str:
        return (f'name: {self.name} {os.linesep}'
                f'value: {self.value} {os.linesep}'
                f'type_hint: {self.type_hint} {os.linesep}'
                f'description: {self.description} {os.linesep}'
                f'tags: {self.tags} {os.linesep}'
                f'is_required: {self.is_required} {os.linesep}'
                f'variants: {self.variants}')

    def __str__(
            self
    ) -> str:
        return self.short_repr()

    def __repr__(
            self
    ) -> str:
        return self.short_repr()

    def __hash__(
            self
    ) -> int:
        return hash(str(self))

    def __eq__(
            self,
            other: type[P]
    ) -> bool:
        """
        Two ``Param`` instances are equal iff they have the same name and value.

        Args:
            other: another ``Param`` instance

        Returns:
            True if the two ``Param`` instances are equal.
        """
        return self.name == other.name and self.value == other.value


class Configuration:
    """
    Generic Configuration class.
    A Configuration specifies the parameters of a Component.
    Configurations store parameters and allow flow control via conditions.

    A ``Configuration`` is a ``Data`` extension specific to ``Component``.
    """

    def __init__(
            self,
            **kwargs
    ):
        if kwargs:
            for k, v in kwargs.items():
                self.add(name=k, value=v)

    def __setattr__(
            self,
            key,
            value
    ):
        self.get(key).value = value

    def __getattribute__(
            self,
            name
    ):
        attr = object.__getattribute__(self, name)
        if isinstance(attr, Param):
            return attr.value
        return attr

    def __str__(
            self
    ) -> str:
        return str(self.to_value_dict())

    # TODO: should we consider conditions as well here?
    def __eq__(
            self,
            other: C
    ):
        if self.params.keys() != other.params.keys():
            return False

        for param_name, param in self.params.items():
            if param.value != other.get(param_name).value:
                return False

        return True

    @property
    def conditions(
            self
    ) -> Dict[str, P]:
        return {key: param for key, param in self.__dict__.items() if
                isinstance(param, Param) and 'condition' in param.tags}

    @property
    def params(
            self
    ) -> Dict[str, P]:
        return {key: param for key, param in self.__dict__.items()
                if isinstance(param, Param) and 'condition' not in param.tags}

    @property
    def values(
            self
    ) -> Dict[str, Any]:
        return {key: param.value for key, param in self.__dict__.items()
                if isinstance(param, Param) and 'condition' not in param.tags}

    # Note: this property works only prior resolution
    @property
    def children(
            self
    ) -> Dict[str, P]:
        return {param_key: param for param_key, param in self.__dict__.items() if param.is_child}

    def get(
            self,
            name: str,
            default: Any = None
    ) -> Optional[P]:
        try:
            return self.__dict__[name]
        except AttributeError:
            return default

    # TODO: add check type condition to variants (if any)?
    # TODO: add allowed range condition to variants (if any)?
    def add(
            self,
            name: str,
            value: Optional[Any] = None,
            type_hint: Optional[Type] = None,
            description: Optional[str] = None,
            tags: Optional[Set[str]] = None,
            allowed_range: Optional[Callable[[Any], bool]] = None,
            is_required: bool = True,
            variants: Optional[Sized] = None,
    ):
        """
        Adds a Parameter to the Configuration via its implicit format.
        By default, Parameter's default conditions are added as well.

        Args:
            name: unique identifier of the Parameter
            value: value of the Parameter
            type_hint: the type hint annotation of ``value``
            description: a string description of the ``Parameter`` for readability purposes
            tags: a set of string tags to mark the ``Parameter`` instance with metadata.
            allowed_range: allowed range of values for ``value``
            is_required: if True, ``value`` cannot be None
            variants: set of variant values of ``value`` of interest
        """
        if name in self.__dict__:
            raise AlreadyExistingParameterException(param=self.get(name))

        self.__dict__[name] = Param(name=name,
                                    value=value,
                                    type_hint=type_hint,
                                    description=description,
                                    tags=tags,
                                    allowed_range=allowed_range,
                                    is_required=is_required,
                                    variants=variants)

        if is_required:
            self.add_condition(name=f'{name}_is_required', condition=partial(is_required_cond, name=name))

        if not self.get(name).is_child and type_hint is not None:
            self.add_condition(name=f'{name}_typecheck',
                               condition=partial(value_typecheck_cond, name=name, type_hint=type_hint),
                               description=f'Checks if {name} if of type {type_hint}.',
                               tags={'typechecking', 'pre-built'})

        if allowed_range is not None:
            self.add_condition(name=f'{name}_allowed_range',
                               condition=partial(allowed_range_cond, name=name),
                               description=f'Checks if {name} is in allowed range.',
                               tags={'allowed_range'})

        if variants is not None:
            self.add_condition(name=f'{name}_valid_variants',
                               condition=partial(valid_variants_cond, name=name),
                               description='Check if variants is not an empty set',
                               tags={'variants'})

    def add_condition(
            self,
            condition: Callable[[Configuration], bool],
            name: str,
            description: Optional[str] = None,
            tags: Tags = None,
    ):
        """
        Adds a condition to be validated.

        Args:
            condition: a function that receives as input the current ``Data`` instance and returns a boolean.
            name: unique identifier.
            description: a string description for readability purposes.
            tags: a set of string tags to mark the condition with metadata.
        """

        tags = set() if tags is None else tags
        tags.add('condition')
        self.add(name=name,
                 value=condition,
                 description=description,
                 tags=tags,
                 is_required=False)

    def validate(
            self,
            strict: bool = True
    ) -> ValidationResult:
        """
        Calls all stage-related conditions to assess the correctness of the current ``Configuration``.

        Args:
            strict: if True, a failed validation process will raise ``InvalidConfigurationException``

        Returns:
            A ``ValidationResult`` object that stores the boolean result of the validation process along with
            an error message if the result is ``False``.

        Raises:
            ``ValidationFailureException``: if ``strict = True`` and the validation process failed
        """

        for child_name, child in self.children.items():
            if isinstance(child.value, Configuration):
                child_validation = child.value.validate(strict=strict)
                if not child_validation.passed:
                    return child_validation

        for condition_name, condition in self.conditions.items():
            if not condition.value(self):
                validation_result = ValidationResult(passed=False,
                                                     error_message=f'Condition {condition_name} failed!',
                                                     source=self.__class__.__name__)
                if strict:
                    raise ValidationFailureException(validation_result=validation_result)

                return validation_result

        return ValidationResult(passed=True, source=self.__class__.__name__)

    def delta_copy(
            self: type[C],
            **kwargs
    ) -> C:
        """
        Gets a delta copy of current ``Configuration``.

        Returns:
            A delta copy of current ``Configuration``.
        """
        copy = deepcopy(self)

        found_keys = []
        for key, value in kwargs.items():
            if key in self.params:
                copy.get(key).value = deepcopy(value)
                found_keys.append(key)

        # Remove found keys
        for key in found_keys:
            kwargs.pop(key)

        if not len(kwargs):
            return copy

        for child_key, child in copy.children.items():
            if isinstance(child.value, cinnamon.configuration.Configuration):
                copy.get(child_key).value = child.value.delta_copy(**kwargs)
            if isinstance(child.value, cinnamon.registry.RegistrationKey):
                raise RuntimeWarning(f'Found {child.value} registration key. Cannot forward {kwargs} to child. '
                                     f'You should invoke Registry.build_configuration() to use this method correctly')
            if isinstance(child.value, cinnamon.component.Component):
                raise RuntimeWarning(f'Found {child.value} component. Cannot forward {kwargs} to child. '
                                     f'You should invoke Registry.build_configuration() to use this method correctly')

        if len(kwargs):
            raise RuntimeError(f'Expected to not have remaining delta parameters, but got {kwargs}.')

        return copy

    @classmethod
    def default(
            cls: Type[C]
    ) -> C:
        """
        Returns the default Configuration instance.

        Returns:
            Configuration instance.
        """
        return cls()

    def to_value_dict(
            self
    ) -> Dict[str, Any]:
        value_dict = {}
        for param_name, param in self.params.items():
            if isinstance(param.value, Configuration):
                value_dict.update(param.value.to_value_dict())
            elif isinstance(param.value, cinnamon.registry.RegistrationKey):
                if cinnamon.registry.Registry.expanded:
                    value_dict.update(cinnamon.registry.Registry.retrieve_configuration(
                        registration_key=param.value).to_value_dict())
            else:
                value_dict[param_name] = param.value

        return json_normalize(value_dict, sep='.').to_dict(orient='records')[0]

    @property
    def has_variants(
            self
    ) -> bool:
        for param_key, param in self.params.items():
            if param.variants is not None and len(param.variants):
                return True
        return False

    # TODO: we should call child.variants if a child is in config variants.
    # This can only be performed if the Registry has been expanded!
    @property
    def variants(
            self,
    ) -> List[Dict[str, Any]]:
        """
        Gets all possible ``Configuration`` variant combinations of current ``Configuration``
        instance based on specified variants.
        There exist two different methods to specify variants
        - ``Parameter``-based: via ``variants`` attribute of ``Parameter``
        - ``Configuration``-based: via ``@supports_variants`` and ``@add_variant`` decorators

        Returns:
            List of variant combinations.
            Each variant combination is a dictionary with ``Parameter.name`` as keys and ``Parameter.value`` as values
        """

        has_variants = self.has_variants

        parameters = {}
        for param_key, param in self.params.items():
            # Always add param.value to account for all possible combinations
            # TODO: consider defining a special value (e.g., UNSET) to allow None as a normal value
            if has_variants and param.value is not None:
                parameters.setdefault(param_key, [param.value])

            if param.variants is not None and len(param.variants):
                parameters.setdefault(param_key, []).extend(param.variants)
        combinations = get_dict_values_combinations(params_dict=parameters)
        return combinations

    def show(
            self,
    ):
        """
        Displays ``Configuration`` parameters.
        """
        logger.info(f'Displaying {self.__class__.__name__} parameters...')
        parameters_repr = os.linesep.join(
            [f'{key}: {value}' for key, value in self.to_value_dict().items()])
        logger.info(parameters_repr)

    def search_param_by_tag(
            self,
            tags: Union[Tags, str],
            exact_match: bool = True
    ) -> Dict[str, Any]:
        """
        Searches for all ``Param`` that match specified tags set.

        Args:
            tags: a set of string tags to look for
            exact_match: if True, only the ``Param`` with ``Param.tags`` that exactly match ``tags`` will be returned

        Returns:
            A dictionary with ``Param.name`` as keys and ``Param`` as values
        """
        if not type(tags) == set:
            tags = {tags}

        return {key: param.value for key, param in self.params.items()
                if (exact_match and param.tags == tags) or (not exact_match and param.tags.intersection(tags) == tags)}

    def search_param(
            self,
            conditions: List[Callable[[P], bool]]
    ) -> Dict[str, Any]:
        """
        Performs a custom ``Param`` search by given conditions.

        Args:
            conditions: list of callable filter functions

        Returns:
            A dictionary with ``Param.name`` as keys and ``Param`` as values
        """
        return {key: param.value for key, param in self.params.items()
                if all([condition(param) for condition in conditions])}
