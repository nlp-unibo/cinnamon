from pathlib import Path
from typing import Union, List
import json


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
