import argparse
import logging
import sys
from logging import getLogger
from typing import Optional

import pandas as pd

from cinnamon.component import RunnableComponent
from cinnamon.registry import Registry, RegistrationKey
from cinnamon.utility.sanity import check_directory, check_external_json_path

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

    valid_df = pd.DataFrame([key.to_record() for key in valid_keys.keys],
                            columns=['Name', 'Tags', 'Namespace', 'Description', 'Metadata'])
    invalid_df = pd.DataFrame([key.to_record() for key in invalid_keys.keys],
                              columns=['Name', 'Tags', 'Namespace', 'Description', 'Metadata'])

    valid_df.to_csv(path_or_buf=registration_path.joinpath('valid_keys.csv'), index=None)
    invalid_df.to_csv(path_or_buf=registration_path.joinpath('invalid_keys.csv'), index=None)

    logger.info('Valid registration keys:')
    for key in valid_keys.keys:
        logger.info(key)

    logger.info('\n')
    logger.info('*' * 50)
    logger.info('\n')

    logger.info('Invalid registration keys:')
    for key in invalid_keys.keys:
        logger.info(key)


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument('-dir', '--directory', type=str)
    parser.add_argument('-ext', '--external-path', type=Optional[str], default=None)
    parser.add_argument('-save', '--save-directory', type=Optional[str], default=None)
    parser.add_argument('-n', '--name', type=str)
    parser.add_argument('-t', '--tags', nargs='+', default=[])
    parser.add_argument('-ns', '--namespace', type=str)
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

    Registry.setup(
        directory=directory,
        external_directories=external_directories,
        save_directory=save_directory
    )

    key = RegistrationKey.parse(name=args.name, tags=args.tags, namespace=args.namespace)
    component = RunnableComponent.build_component(registration_key=key)

    if not isinstance(component, RunnableComponent):
        raise RuntimeError(f'Attempting to run a Component that is not a runnable one. '
                           f'Make sure your component inherits from {RunnableComponent} and implement the `run` method')

    component.run()
