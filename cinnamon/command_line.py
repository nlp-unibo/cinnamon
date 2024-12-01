import argparse
import json
import logging
from logging import getLogger
from typing import Optional, List

from cinnamon.registry import Registry, RegistrationKey
from cinnamon.utility.sanity import check_directory, check_external_json_path
import sys

logging.basicConfig(
    level=logging.INFO,
    encoding='utf-8'
)
logger = getLogger(__name__)


def setup():
    parser = argparse.ArgumentParser()
    parser.add_argument('-dir', '--directory', type=str)
    parser.add_argument('-ext', '--external-path', type=Optional[str], default=None)
    parser.add_argument('-save', '--save-directory', type=Optional[str], default=None)
    args = parser.parse_args()

    directory = check_directory(directory_path=args.directory)
    external_directories = None
    save_directory = None

    if args.external_path is not None:
        external_directories = check_external_json_path(jsonpath=args.external_path)

    if args.save_directory is not None:
        save_directory = check_directory(directory_path=args.save_directory)

    logger.info(f"""Loading cinnamon registrations using:
        Directory: {directory}
        External dependencies: {external_directories}
        Git save directory: {save_directory}
    """)

    # add to PYTHONPATH
    sys.path.insert(0, directory.as_posix())

    valid_keys, invalid_keys = Registry.setup(
        directory=directory,
        external_directories=external_directories,
        save_directory=save_directory
    )

    registration_path = directory.joinpath('registrations')
    if not registration_path.exists():
        registration_path.mkdir(parents=True, exist_ok=True)

    with registration_path.joinpath('valid_keys.json').open('w') as f:
        json.dump([key.toJSON() for key in valid_keys], f)

    with registration_path.joinpath('invalid_keys.json').open('w') as f:
        json.dump([key.toJSON() for key in invalid_keys], f)

    logger.info('Valid registration keys:')
    Registry.show_registrations(keys=valid_keys)

    logger.info('\n')
    logger.info('*' * 50)
    logger.info('\n')

    logger.info('Invalid registration keys:')
    Registry.show_registrations(keys=invalid_keys)
