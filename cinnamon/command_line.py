import argparse
import logging
import os
import sys
from logging import getLogger
from typing import Optional

import pandas as pd
from InquirerPy import inquirer

from cinnamon.component import RunnableComponent
from cinnamon.registry import Registry
from cinnamon.utility.inquirer import filter_keys
from cinnamon.utility.sanity import check_directory, check_external_json_path

logging.basicConfig(
    level=logging.INFO,
    encoding='utf-8'
)
logger = getLogger(__name__)


# TODO: add option to filter namespaces? -> directly in dag_resolution
# TODO: make interactive
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
    valid_df = valid_df.sort_values(by=['Name'])
    invalid_df = pd.DataFrame([key.to_record() for key in invalid_keys.keys],
                              columns=['Name', 'Tags', 'Namespace', 'Description', 'Metadata'])
    invalid_df = invalid_df.sort_values(by=['Name'])

    valid_df.to_csv(registration_path.joinpath('valid_keys.csv'), index=None)
    invalid_df.to_csv(registration_path.joinpath('invalid_keys.csv'), index=None)

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

    keys = [key for key in valid_keys.keys if 'runnable' in key.tags]

    if not len(keys):
        logger.info(f'Could not find any registered runnable component out of {len(valid_keys.keys)}. Aborting...')
        return

    filtered_keys = []
    while not len(filtered_keys):
        filtered_keys = filter_keys(keys=keys)

    logger.info(f'You have selected the following keys to execute: '
                f'{os.linesep.join([str(item) for item in filtered_keys])}')

    action = inquirer.confirm(message='Proceed?', default=True).execute()

    if not action:
        return

    for key in filtered_keys:
        logger.info(f'Executing {key}')
        component = RunnableComponent.build_component(registration_key=key)
        component.run()
