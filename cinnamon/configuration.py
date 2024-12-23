from __future__ import annotations

import logging
import os
from copy import deepcopy
from functools import partial
from typing import Dict, Any, Callable, Optional, TypeVar, Sized, List, Set, Union, Type

from pandas import json_normalize

import cinnamon.component
import cinnamon.registry
from cinnamon.utility.configuration import get_dict_values_combinations
from cinnamon.utility.exceptions import (
    AlreadyExistingParameterException
)
from cinnamon.utility.sanity import (
    ValidationResult,
    ValidationFailureException,
    is_required_cond,
    allowed_range_cond,
)

C = TypeVar('C', bound='Configuration')
P = TypeVar('P', bound='Param')

Constructor = Callable[[Any], C]
Tags = Optional[Set[str]]
Condition = Callable[["Configuration"], bool]

__all__ = [
    'Configuration',
    'C',
    'P',
    'Tags',
    'Param'
]

logger = logging.getLogger(__name__)


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

        if self.is_dependency:
            self.tags.add('dependency')

    @property
    def is_dependency(
            self
    ) -> bool:
        return ('dependency' in self.tags
                or type(self.value) == cinnamon.registry.RegistrationKey
                or type(self.value) == Optional[cinnamon.registry.RegistrationKey]
                or self.type_hint == cinnamon.registry.RegistrationKey
                or self.type_hint == Optional[cinnamon.registry.RegistrationKey]
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

    def __setattr__(
            self,
            key,
            value
    ):
        if key in self.params:
            self.params.get(key).value = value
        else:
            super().__setattr__(key, value)

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
                isinstance(param, Param) and 'condition' in param.tags or 'pre-condition' in param.tags}

    @property
    def params(
            self
    ) -> Dict[str, P]:
        return {key: param for key, param in self.__dict__.items()
                if isinstance(param, Param) and param.tags.intersection({'condition', 'pre-condition'}) == set()}

    @property
    def values(
            self
    ) -> Dict[str, Any]:
        return {key: param.value for key, param in self.__dict__.items()
                if isinstance(param, Param) and param.tags.intersection({'condition', 'pre-condition'}) == set()}

    # Note: this property works only prior resolution
    @property
    def dependencies(
            self
    ) -> Dict[str, P]:
        return {param_key: param for param_key, param in self.__dict__.items() if param.is_dependency}

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
            self.add_condition(name=f'{name}_is_required',
                               condition=partial(is_required_cond, name=name))

        if allowed_range is not None:
            self.add_condition(name=f'{name}_allowed_range',
                               condition=partial(allowed_range_cond, name=name),
                               description=f'Checks if {name} is in allowed range.',
                               is_pre_condition=self.get(name).is_dependency)


    def add_condition(
            self,
            condition: Condition,
            name: str,
            description: Optional[str] = None,
            tags: Tags = None,
            is_pre_condition: bool = False
    ):
        """
        Adds a condition to be validated.

        Args:
            condition: a function that receives as input the current ``Data`` instance and returns a boolean.
            name: unique identifier.
            description: a string description for readability purposes.
            tags: a set of string tags to mark the condition with metadata.
            is_pre_condition: TODO
        """

        tags = set() if tags is None else tags
        tags.add('condition')
        if is_pre_condition:
            tags.add('pre-condition')
        self.add(name=name,
                 value=condition,
                 description=description,
                 tags=tags,
                 is_required=False)

    def _validate(
            self,
            conditions: List[Param],
            strict: bool = True,
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

        for condition in conditions:
            if not condition.value(self):
                validation_result = ValidationResult(passed=False,
                                                     error_message=f'Condition {condition.name} failed!',
                                                     source=self.__class__.__name__)
                if strict:
                    raise ValidationFailureException(validation_result=validation_result)

                return validation_result

        return ValidationResult(passed=True, source=self.__class__.__name__)

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

        for child_name, child in self.dependencies.items():
            if isinstance(child.value, Configuration):
                child_validation = child.value.validate(strict=strict)
                if not child_validation.passed:
                    return child_validation

        conditions = self.search_condition_by_tag(tags={'condition'}, exact_match=False)
        return self._validate(conditions=conditions, strict=strict)

    def pre_validate(
            self,
            strict: bool = True
    ) -> ValidationResult:
        conditions = self.search_condition_by_tag(tags={'pre-condition'}, exact_match=False)
        return self._validate(conditions=conditions, strict=strict)

    def delta_copy(
            self: type[C],
            **kwargs
    ) -> C:
        """
        Gets a delta copy of current ``Configuration``.

        Returns:
            A delta copy of current ``Configuration``.
        """
        copy: C = type(self)()

        # Flat params
        for param_name, param in self.params.items():
            if param_name in kwargs:
                value = deepcopy(kwargs[param_name])
                kwargs.pop(param_name)
            else:
                value = deepcopy(param.value)

            copy.add(name=param_name,
                     value=deepcopy(value),
                     type_hint=param.type_hint,
                     description=param.description,
                     is_required=param.is_required,
                     tags=param.tags,
                     variants=param.variants,
                     allowed_range=param.allowed_range)

        # Custom conditions
        for name, condition in self.conditions.items():
            if name not in copy.conditions:
                copy.add_condition(name=name,
                                   condition=deepcopy(condition),
                                   description=condition.description,
                                   tags=condition.tags,
                                   is_pre_condition='pre-condition' in condition.tags)

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

        if not len(value_dict):
            return value_dict

        return json_normalize(value_dict, sep='.').to_dict(orient='records')[0]

    @property
    def has_variants(
            self
    ) -> bool:
        for param_key, param in self.params.items():
            if param.variants is not None and len(param.variants):
                return True
        return False

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
        params_with_variants = []
        for param_key, param in self.params.items():
            # Always add param.value to account for all possible combinations
            # TODO: consider defining a special value (e.g., UNSET) to allow None as a normal value
            if has_variants and param.value is not None:
                parameters.setdefault(param_key, [param.value])

            if param.variants is not None and len(param.variants):
                parameters.setdefault(param_key, []).extend(param.variants)
                params_with_variants.append(param_key)
        combinations = [{key: value for key, value in comb.items() if key in params_with_variants}
                        for comb in get_dict_values_combinations(params_dict=parameters)]
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

    def _search(
            self,
            conditions: List[Callable[[Any], bool]],
            buffer: Dict[str, Any]
    ) -> List[Any]:
        return [value for key, value in buffer.items() if all([condition(value) for condition in conditions])]

    def search_param_by_tag(
            self,
            tags: Union[Tags, str],
            exact_match: bool = True
    ) -> List[Param]:
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

        return self._search(buffer=self.params,
                            conditions=[
                                lambda p: (p.tags == tags and exact_match) or (
                                        not exact_match and p.tags.intersection(tags) == tags)
                            ])

    def search_param(
            self,
            conditions: List[Callable[[P], bool]]
    ) -> List[Param]:
        """
        Performs a custom ``Param`` search by given conditions.

        Args:
            conditions: list of callable filter functions

        Returns:
            A dictionary with ``Param.name`` as keys and ``Param`` as values
        """
        return self._search(conditions=conditions, buffer=self.params)

    def search_condition_by_tag(
            self,
            tags: Union[Tags, str],
            exact_match: bool = True
    ) -> List[Param]:
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

        return self._search(buffer=self.conditions,
                            conditions=[
                                lambda p: (p.tags == tags and exact_match) or (
                                        not exact_match and p.tags.intersection(tags) == tags)
                            ])

    def search_condition(
            self,
            conditions: List[Callable[[Condition], bool]]
    ) -> List[Param]:
        return self._search(conditions=conditions, buffer=self.conditions)
