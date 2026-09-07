from __future__ import annotations

import json
import time
from functools import wraps
from logging import getLogger
from pathlib import Path
from typing import List, Optional, Union

logger = getLogger(__name__)

__all__ = ["check_directory", "check_external_json_path", "time_it"]


def check_directory(directory_path: Optional[Union[Path, str]] = None) -> Path:
    directory_path = Path(directory_path) if directory_path else Path(".")
    directory_path = directory_path.resolve()
    if not directory_path.exists():
        raise FileNotFoundError(f"Directory {directory_path} does not exist!")

    if not directory_path.is_dir():
        raise NotADirectoryError(f"{directory_path} is not a directory!")

    return directory_path


def check_external_json_path(jsonpath: Union[Path, str]) -> List[str]:
    """Read and validate a JSON file listing external configuration directories.

    The contract is a JSON array of directory paths, as strings::

        ["/path/to/external/project_a", "/path/to/external/project_b"]

    The structure is checked here rather than downstream because this file is an
    input boundary: it is hand-written, and it is the file a future remote-source
    feature would grow into. Without the check, the shape only failed later --
    ``resolve_external_directories`` calls ``Path()`` on each entry, so a JSON
    object reached the user as ``TypeError: argument should be a str or an
    os.PathLike object where __fspath__ returns a str, not <class 'dict'>``,
    which names neither the file nor the offending entry.

    Existence and directory-ness are *not* checked here --
    :meth:`Registry.resolve_external_directories` already does that, and raises
    ``InvalidDirectoryException`` naming the directory.

    Returns:
        The list of directory paths, unchanged.

    Raises:
        ``FileNotFoundError``: if *jsonpath* does not exist.
        ``TypeError``: if *jsonpath* is not a ``.json`` file, if it does not
            contain a list, or if an entry is not a string.
        ``ValueError``: if an entry is empty or only whitespace.
    """
    jsonpath = Path(jsonpath).resolve()

    if not jsonpath.exists():
        raise FileNotFoundError(
            f"External directory JSON path {jsonpath} does not exist!"
        )

    if jsonpath.suffix.casefold() != ".json":
        raise TypeError(f"External directory JSON path {jsonpath} is not a JSON file!")

    with jsonpath.open("r") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise TypeError(
            f"External directory JSON {jsonpath} must contain a list of directory "
            f"paths, found {type(data).__name__}."
        )

    for index, entry in enumerate(data):
        if not isinstance(entry, str):
            raise TypeError(
                f"External directory JSON {jsonpath}, entry {index}: expected a "
                f"directory path as a string, found {type(entry).__name__} "
                f"({entry!r})."
            )
        if not entry.strip():
            raise ValueError(
                f"External directory JSON {jsonpath}, entry {index}: "
                f"directory path is empty."
            )

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
