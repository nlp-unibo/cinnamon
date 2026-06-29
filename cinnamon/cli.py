import argparse
import logging
import os
import sys
from logging import getLogger

import pandas as pd
from InquirerPy import inquirer

from cinnamon.registry import Registry
from cinnamon.utility.inquirer import filter_keys
from cinnamon.utility.sanity import check_directory, check_external_json_path

logging.basicConfig(level=logging.INFO, encoding="utf-8")
logger = getLogger(__name__)


def build():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-dir",
        "--directory",
        type=str,
        help="Directory containing cinnamon registrations",
    )
    parser.add_argument(
        "-ext",
        "--external-path",
        type=str,
        default=None,
        help="Path to file containing all external directories",
    )
    args = parser.parse_args()

    directory = check_directory(directory_path=args.directory)
    external_directories = None

    if args.external_path is not None:
        external_directories = check_external_json_path(jsonpath=args.external_path)

    logger.info(f"""Loading cinnamon registrations using:
        Directory: {directory}
        External directories: {external_directories}
    """)

    # add to PYTHONPATH
    sys.path.insert(0, directory.as_posix())

    valid_keys, invalid_keys = Registry.build(
        directory=directory, external_directories=external_directories
    )

    registration_path = directory.joinpath("registrations")
    if not registration_path.exists():
        registration_path.mkdir(parents=True, exist_ok=True)

    valid_df = pd.DataFrame(
        [key.to_record() for key in valid_keys],
        columns=["Name", "Tags", "Namespace", "Description", "Metadata"],
    )
    valid_df = valid_df.sort_values(by=["Name"])
    invalid_df = pd.DataFrame(
        [key.to_record() for key in invalid_keys],
        columns=["Name", "Tags", "Namespace", "Description", "Metadata"],
    )
    invalid_df = invalid_df.sort_values(by=["Name"])

    valid_df.to_csv(registration_path.joinpath("valid_keys.csv"), index=None)
    invalid_df.to_csv(registration_path.joinpath("invalid_keys.csv"), index=None)

    logger.info("Valid registration keys:")
    for key in valid_keys:
        logger.info(key)

    logger.info("\n")
    logger.info("*" * 50)
    logger.info("\n")

    logger.info("Invalid registration keys:")
    for key in invalid_keys:
        logger.info(key)


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-dir",
        "--directory",
        type=str,
        help="Directory containing cinnamon registrations",
    )
    parser.add_argument(
        "-ext",
        "--external-path",
        type=str,
        default=None,
        help="Path to file containing all external directories",
    )
    args = parser.parse_args()

    directory = check_directory(directory_path=args.directory)
    external_directories = None

    if args.external_path is not None:
        external_directories = check_external_json_path(jsonpath=args.external_path)

    logger.info(f"""Loading cinnamon registrations using:
        Directory: {directory}
        External directories: {external_directories}
    """)

    # add to PYTHONPATH
    sys.path.insert(0, directory.as_posix())

    Registry.build(directory=directory, external_directories=external_directories)
    keys = Registry.retrieve_runnable_keys()

    if not len(keys):
        logger.info(f"Could not find any registered runnable component. Aborting...")
        return

    filtered_keys = []
    while not len(filtered_keys):
        filtered_keys = filter_keys(keys=list(keys))

    logger.info(
        f"You have selected the following keys to execute: {os.linesep}"
        f"{os.linesep.join([f'{idx + 1}. {str(item)}' for idx, item in enumerate(filtered_keys)])}"
    )

    action = inquirer.confirm(message="Proceed?", default=True).execute()

    if not action:
        return

    for key in filtered_keys:
        logging.info(f"Executing {key}")

        config_info = Registry.retrieve_configuration_info(registration_key=key)
        config_info.config.show()

        component = Registry.instantiate_component(registration_key=key)

        # config_info.run_method is not None here
        if hasattr(component, config_info.run_method):
            getattr(component, config_info.run_method)()
        else:
            logging.error(
                f"Component {component} has not method {config_info.run_method}! Aborting..."
            )
            raise RuntimeError(
                f"Component {component} has not method {config_info.run_method}! Aborting..."
            )


def generate():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-dir",
        "--directory",
        type=str,
        help="Directory containing cinnamon registrations",
    )
    parser.add_argument(
        "-run-dir",
        "--run-directory",
        type=str,
        help="Directory where to generate script",
    )
    parser.add_argument(
        "-name", "--filename", type=str, help="Generated script filename", required=True
    )
    parser.add_argument(
        "-ext",
        "--external-path",
        type=str,
        default=None,
        help="Path to file containing all external directories",
    )
    args = parser.parse_args()

    directory = check_directory(directory_path=args.directory)
    run_directory = check_directory(directory_path=args.run_directory)
    external_directories = None

    if args.external_path is not None:
        external_directories = check_external_json_path(jsonpath=args.external_path)

    logger.info(f"""Loading cinnamon registrations using:
            Directory: {directory}
            External directories: {external_directories}
        """)

    # add to PYTHONPATH
    sys.path.insert(0, directory.as_posix())

    valid_keys, invalid_keys = Registry.build(
        directory=directory, external_directories=external_directories
    )

    if not len(valid_keys):
        logger.info(f"Could not find any registered runnable component. Aborting...")
        return

    filtered_keys = []
    while not len(filtered_keys):
        filtered_keys = filter_keys(keys=list(valid_keys))

    logger.info(
        f"You have selected the following keys to execute: {os.linesep}"
        f"{os.linesep.join([f'{idx + 1}. {str(item)}' for idx, item in enumerate(filtered_keys)])}"
    )

    action = inquirer.confirm(message="Proceed?", default=True).execute()

    if not action:
        return

    code_keys = f",{os.linesep}".join([f'"{str(key)}"' for key in filtered_keys])

    code_template = f"""
# Automatically generated via cmn-generate
import logging
from pathlib import Path
from cinnamon.registry import Registry, RegistrationKey

if __name__ == '__main__':
    Registry.build(directory=Path('{run_directory}'))
    logging.basicConfig()
    
    keys = [
        {code_keys}
]
    
    # Use RegistrationKey.from_string() to retrieve the RegistrationKey instance from string
    for key in keys:
        key = RegistrationKey.from_string(key)

        config_info = Registry.retrieve_configuration_info(registration_key=key)
        config_info.config.show()

        component = Registry.instantiate_component(registration_key=key)

        if hasattr(component, config_info.run_method):
            getattr(component, config_info.run_method)()
    """

    script_path = run_directory.joinpath(f"{args.filename}.py")
    if script_path.exists():
        response = input(
            f"Script path {script_path} already exists. Do you want to overwrite it? Y/N "
        )
        if response.strip().casefold() != "y":
            logger.info("Aborting...")
            return

    with open(script_path, "w") as f:
        f.write(code_template)
