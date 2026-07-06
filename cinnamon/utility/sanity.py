from __future__ import annotations

import json
import time
from functools import wraps
from logging import getLogger
from pathlib import Path
from typing import List, Union

logger = getLogger(__name__)

__all__ = ["check_directory", "check_external_json_path", "time_it"]


def check_directory(directory_path: Union[Path, str] = None) -> Path:
    directory_path = (
        directory_path if directory_path is not None else Path(".").resolve()
    )
    directory_path = (
        Path(directory_path) if type(directory_path) != Path else directory_path
    )
    directory_path = directory_path.resolve()
    if not directory_path.exists():
        raise FileNotFoundError(f"Directory {directory_path} does not exist!")

    if not directory_path.is_dir():
        raise NotADirectoryError(f"{directory_path} is not a directory!")

    return directory_path


def check_external_json_path(jsonpath: Union[Path, str]) -> List[Path]:
    jsonpath = Path(jsonpath) if type(jsonpath) != Path else jsonpath
    jsonpath = jsonpath.resolve()

    if not jsonpath.exists():
        raise FileNotFoundError(
            f"External directory JSON path {jsonpath} does not exist!"
        )

    if jsonpath.suffix.casefold() != ".json":
        raise TypeError(f"External directory JSON path {jsonpath} is not a JSON file!")

    with jsonpath.open("r") as f:
        data = json.load(f)

    return data


def time_it(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        logger.info(f"[{func.__name__}] executed in {end - start:.6f} seconds")
        return result

    return wrapper
