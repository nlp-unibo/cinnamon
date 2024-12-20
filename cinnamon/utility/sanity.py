from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Union, List, Optional


def check_directory(
        directory_path: Union[Path, str] = None
) -> Path:
    directory_path = directory_path if directory_path is not None else Path('.').resolve()
    directory_path = Path(directory_path) if type(directory_path) != Path else directory_path
    directory_path = directory_path.resolve()
    if not directory_path.exists():
        raise FileNotFoundError(f'Directory {directory_path} does not exist!')

    if not directory_path.is_dir():
        raise NotADirectoryError(f'{directory_path} is not a directory!')

    return directory_path


def check_external_json_path(
        jsonpath: Union[Path, str]
) -> List[Path]:
    jsonpath = Path(jsonpath) if type(jsonpath) != Path else jsonpath
    jsonpath = jsonpath.resolve()

    if not jsonpath.exists():
        raise FileNotFoundError(f'External directory JSON path {jsonpath} does not exist!')

    if jsonpath.suffix.casefold() != '.json':
        raise TypeError(f'External directory JSON path {jsonpath} is not a JSON file!')

    with jsonpath.open('r') as f:
        data = json.load(f)

    return data


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
        config: "cinnamon.configuration.Configuration",
        name: str
) -> bool:
    return config.get(name).value is not None


def allowed_range_cond(
        config: "cinnamon.configuration.Configuration",
        name: str,
) -> bool:
    found_param = config.get(name)

    if found_param.value is not None and not found_param.allowed_range(found_param.value):
        return False
    return True


def valid_variants_cond(
        config: "cinnamon.configuration.Configuration",
        name: str
):
    return len(config.get(name).variants) > 0
