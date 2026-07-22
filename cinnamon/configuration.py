from __future__ import annotations

import copy
import itertools
import logging
import typing
import warnings
from dataclasses import dataclass
from typing import (
    Any,
    Callable,
    ClassVar,
    Dict,
    List,
    Mapping,
    Set,
    Type,
    TypeVar,
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PrivateAttr,
    model_validator,
)
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined
from typing_extensions import Self

import cinnamon.registry
from cinnamon.utility.exceptions import (
    ValidationFailureException,
    ValidationResult,
)
from cinnamon.utility.registration import Tags

C = TypeVar("C", bound="Configuration")

Constructor = Callable[[Any], C]
Condition = Callable[["Configuration"], bool]

__all__ = ["Configuration", "C", "Param"]

logger = logging.getLogger(__name__)


@dataclass
class ConditionInfo:
    condition: Condition
    tags: Tags
    description: str | None = None


class ParamMeta:
    def __init__(self, tags: Set[str], variants: List[Any]):
        self.tags = tags
        self.variants = variants

    def __call__(self, schema: dict) -> None:
        pass


def Param(
    default: Any = PydanticUndefined,
    *,
    description: str | None = None,
    tags: Set[str] | None = None,
    variants: List[Any] | None = None,
    **kwargs: Any,
) -> Any:
    return Field(
        default,
        description=description,
        json_schema_extra=ParamMeta(
            tags=tags or set(),
            variants=variants or [],
        ),
        **kwargs,
    )


class FieldMetaProxy:
    """Navigates your metadata maps depending on context."""

    def __init__(self, source_dict: dict, is_instance: bool):
        self._source = source_dict
        self._is_instance = is_instance

    def __getattr__(self, field_name: str) -> ParamMeta:
        if field_name not in self._source:
            raise AttributeError(f"No field named '{field_name}'")

        if self._is_instance:
            return self._source[field_name]
        else:
            field_info = self._source[field_name]
            if field_info.json_schema_extra is None:
                field_info.json_schema_extra = ParamMeta(tags=set(), variants=[])
            return field_info.json_schema_extra

    def get(self, field_name: str) -> ParamMeta:
        """Allows dynamic string access via .get()"""
        try:
            return self.__getattr__(field_name)
        except AttributeError:
            raise KeyError(f"No field named '{field_name}'")

    def __getitem__(self, field_name: str) -> ParamMeta:
        """Allows dictionary bracket access: self.meta[field_name]"""
        return self.get(field_name)


class MetaDescriptor:
    """
    A descriptor that automatically distinguishes class-level vs instance-level access.
    """

    def __get__(self, instance: Any, owner: type) -> FieldMetaProxy:
        if instance is None:
            # Triggered by: MyConfig.meta.x.variants (Class context)
            return FieldMetaProxy(owner.model_fields, is_instance=False)
        else:
            # Triggered by: config.meta.x.variants (Instance context)
            return FieldMetaProxy(instance._instance_meta, is_instance=True)


class Configuration(BaseModel):
    """
    A Configuration specifies the parameters of a Component.
    Configurations store parameters and allow flow control via conditions.
    """

    _conditions: Dict[str, ConditionInfo] = PrivateAttr(default_factory=dict)
    _expanded: bool = PrivateAttr(default=False)

    # ignore this variable during serialization
    _instance_meta: Dict[str, ParamMeta] = PrivateAttr(default_factory=dict)

    meta: ClassVar[MetaDescriptor] = MetaDescriptor()

    model_config = ConfigDict(validate_default=True)

    def model_post_init(self, __context: Any) -> None:
        """Runs automatically right after Pydantic instantiates an object."""
        instance_map = {}
        for field_name, field_info in self.fields.items():
            extra = field_info.json_schema_extra or ParamMeta(tags=set(), variants=[])
            instance_map[field_name] = copy.deepcopy(extra)

        # Safely assign to our private attribute using object.__setattr__
        object.__setattr__(self, "_instance_meta", instance_map)

    @classmethod
    def retrieve(
        cls: Type[C],
        registration_key: cinnamon.registry.Registration | None = None,
        name: str | None = None,
        namespace: str | None = None,
        tags: Tags = None,
    ) -> C:
        """
        Syntactic sugar for retrieving a `Configuration` from a
         ``RegistrationKey`` in implicit format.

        Args:
            registration_key: the ``RegistrationKey`` used to register the
             ``Configuration`` class.
            name: the ``name`` field of ``RegistrationKey``
            tags: the ``tags`` field of ``RegistrationKey``
            namespace: the ``namespace`` field of ``RegistrationKey``

        Returns:
            A ``Configuration`` instance

        Raises:
            ``InvalidConfigurationTypeException``: if there's a mismatch
             between the ``Configuration`` class used
            during registration and the type of the built ``Configuration``
             instance using the registered
            ``constructor`` method (see ``ConfigurationInfo`` arguments).
        """
        config = cinnamon.registry.Registry.retrieve_configuration(
            registration_key=registration_key, name=name, tags=tags, namespace=namespace
        )
        if not isinstance(config, cls):
            raise RuntimeError(
                f"The instantiated config is not an instance of {cls}."
                f" Got {config.__class__.__name__}"
            )

        return config

    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs: Any) -> None:
        super().__pydantic_init_subclass__(**kwargs)

        for field_name, field_info in cls.model_fields.items():
            if field_info.json_schema_extra is None:
                field_info.json_schema_extra = ParamMeta(tags=set(), variants=[])

    @model_validator(mode="after")
    def validate_variants(self) -> C:
        for field_name, field_info in self.fields.items():
            field_variants = self.meta[field_name].variants
            if not field_variants:
                continue

            default_value = field_info.default
            if (
                default_value is PydanticUndefined
                or field_info.default_factory is not None
            ):
                continue  # required fields have no default to check

            if default_value in field_variants:
                raise ValueError(
                    f"Default value '{default_value}' for field '{field_name}' "
                    f"is also reported in variants. This is not allowed."
                )
        return self

    def model_copy(
        self, *, update: Mapping[str, Any] | None = None, deep: bool = False
    ) -> Self:
        # 1. Get a pydantic copy with the updates applied
        model_copy = super().model_copy(update=update, deep=deep)

        # 2. Re-validate public fields only (this is what was broken before —
        #    the old code discarded the validated result)
        validated = self.model_validate(model_copy.model_dump(mode="python"))

        # 3. Manually propagate private attributes that model_validate doesn't touch
        conditions = copy.deepcopy(self._conditions) if deep else dict(self._conditions)
        object.__setattr__(validated, "_conditions", conditions)
        object.__setattr__(validated, "_expanded", self._expanded)

        return validated

    def is_dependency(self, field_name: str, field: FieldInfo) -> bool:
        field_value = getattr(self, field_name)
        annotation = field.annotation
        args = typing.get_args(annotation)
        actual_type = args[0] if args else annotation
        return (
            isinstance(field_value, cinnamon.registry.RegistrationKey)
            or isinstance(field_value, Configuration)
            or actual_type is cinnamon.registry.RegistrationKey
            or actual_type is Configuration
        )

    @property
    def expanded(self) -> bool:
        return self._expanded

    @expanded.setter
    def expanded(self, expanded: bool) -> None:
        self._expanded = expanded

    @property
    def fields(self) -> Dict[str, FieldInfo]:
        return self.__class__.model_fields

    @property
    def values(self) -> Dict[str, Any]:
        return {
            field_name: getattr(self, field_name)
            for field_name, field in self.fields.items()
        }

    @property
    def dependencies(
        self,
    ) -> Dict[str, cinnamon.registry.RegistrationKey | Configuration]:
        return {
            field_name: getattr(self, field_name)
            for field_name, field in self.fields.items()
            if self.is_dependency(field_name=field_name, field=field)
        }

    def add_condition(
        self,
        condition: Condition,
        name: str,
        description: str | None = None,
        tags: Tags = None,
    ):
        """
        Adds a condition to be validated.

        Args:
            condition: a function that receives as input the current
             ``Configuration`` instance and returns a boolean.
            name: unique identifier.
            description: a string description for readability purposes.
            tags: a set of string tags to mark the condition with metadata.

        Raises:
            ``AlreadyExistingParameterException``: if the provided `name`
             already exists in the Configuration instance.
        """
        if name in self._conditions:
            warnings.warn(
                "Condition with name {name} already exists! Overwriting...",
                RuntimeWarning
            )

        self._conditions[name] = ConditionInfo(
            condition=condition, description=description, tags=tags
        )

    def validate_conditions(self, strict: bool = True) -> ValidationResult:
        """
        Validates all provided conditions related to the ``Configuration`` instance.

         Args:
             strict: if True, a failed validation process will raise
              ``InvalidConfigurationException``

         Returns:
             A ``ValidationResult`` that stores the boolean result of the validation
              process along with an error message if the result is ``False``.

         Raises:
             ``ValidationFailureException``: if ``strict = True`` and the validation
              process failed
        """

        for dependency_name, dependency in self.dependencies.items():
            if isinstance(dependency, Configuration):
                child_validation = dependency.validate_conditions(strict=strict)
                if not child_validation.passed:
                    return child_validation

        for condition_name, condition_info in self._conditions.items():
            if not condition_info.condition(self):
                validation_result = ValidationResult(
                    passed=False,
                    error_message=f"Condition {condition_name} failed!",
                    source=self.__class__.__name__,
                )
                if strict:
                    raise ValidationFailureException(
                        validation_result=validation_result
                    )

                return validation_result

        return ValidationResult(passed=True, source=self.__class__.__name__)

    @classmethod
    def default(cls: Type[C]) -> C:
        """
        Returns the default ``Configuration`` instance.

        Returns:
            ``Configuration`` instance.
        """
        return cls()

    @property
    def has_variants(self) -> bool:
        for field_name, field_info in self.fields.items():
            if len(self.meta[field_name].variants):
                return True
        return False

    @property
    def has_at_least_two_variants(self) -> bool:
        field_with_variants = 0
        for field_name, field_info in self.fields.items():
            if len(self.meta[field_name].variants):
                field_with_variants += 1
            if field_with_variants >= 2:
                return True
        return False

    @property
    def variants(
        self,
    ) -> List[Dict[str, Dict[str, Any]]]:
        """
        Computes all unique combinations of a configuration's fields along
         with their indices.
        The baseline/default value always gets index 0.
        Subsequent unique variants get an increasing index (1, 2, ...).
        """
        field_choices = {}

        if not self.has_variants:
            return []

        for field_name in self.fields.keys():
            current_value = getattr(self, field_name)
            variants = self.meta[field_name].variants or []

            field_choices[field_name] = [
                (item, idx + 1) for idx, item in enumerate(variants)
            ]

            if len(self.fields) > 1:
                field_choices[field_name].insert(0, (current_value, 0))

        # Unpack keys and their list of (value, index) tuples
        keys = list(field_choices.keys())
        value_lists = list(field_choices.values())

        combinations = []
        # ((val_x, idx_x), (val_y, idx_y), ...)
        for combination_tuple in itertools.product(*value_lists):
            combo_values = {}
            combo_indexes = {}

            for key, (val, idx) in zip(keys, combination_tuple):
                combo_values[key] = val
                combo_indexes[key] = idx

            # exclude default configuration
            if sum(list(combo_indexes.values())) == 0:
                continue

            combinations.append({"values": combo_values, "indexes": combo_indexes})

        return combinations
