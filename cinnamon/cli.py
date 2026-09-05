import argparse
import json
import logging
import os
import sys
from logging import getLogger
from pathlib import Path
from typing import List, Optional, Tuple

from cinnamon.registry import RegistrationKey, Registry
from cinnamon.utility import key_analyzer
from cinnamon.utility.inquirer import filter_keys
from cinnamon.utility.key_analyzer import (
    analyze_keys,
    explain_variant_tags,
    format_findings,
    format_variant_explanations,
)
from cinnamon.utility.sanity import check_directory, check_external_json_path
from cinnamon.utility.static_analyzer import analyze_registry, print_analysis_summary

logger = getLogger(__name__)


def _configure_logging() -> None:
    """Configure root logging for a console entry point.

    Called from the ``cmn-*`` functions rather than at import time: a library
    module that calls ``basicConfig`` on import reconfigures logging for every
    application that imports it.
    """
    logging.basicConfig(level=logging.INFO)


def _require_inquirer():
    try:
        from InquirerPy import inquirer

        return inquirer
    except ImportError:
        raise ImportError(
            "InquirerPy is required for the CLI. "
            "Install it with: pip install cinnamon[cli]"
        ) from None


def _build_parser(
    *,
    run_directory: bool = False,
    filename: bool = False,
    strict: bool = False,
):
    """Assemble the argument parser shared by every ``cmn-*`` entry point."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-dir",
        "--directory",
        type=str,
        help="Directory containing cinnamon registrations",
    )
    if run_directory:
        parser.add_argument(
            "-run-dir",
            "--run-directory",
            type=str,
            help="Directory where to generate script",
        )
    if filename:
        parser.add_argument(
            "-name",
            "--filename",
            type=str,
            help="Generated script filename",
            required=True,
        )
    parser.add_argument(
        "-ext",
        "--external-path",
        type=str,
        default=None,
        help="Path to file containing all external directories",
    )
    if strict:
        parser.add_argument(
            "--strict",
            action="store_true",
            help="Treat warnings as failures",
        )
        parser.add_argument(
            "--deep",
            action="store_true",
            help=(
                "Import every component to check its __init__ against the "
                "configuration's fields. Slower: the cost is that of importing "
                "your components, not of the registry"
            ),
        )
    return parser


def _resolve_sources(args) -> Tuple[Path, Optional[List[Path]]]:
    """Validate the requested paths, log them, and put *directory* on the path."""
    directory = check_directory(directory_path=args.directory)
    external_directories = None

    if args.external_path is not None:
        external_directories = check_external_json_path(jsonpath=args.external_path)

    logger.info(f"""Loading cinnamon registrations using:
        Directory: {directory}
        External directories: {external_directories}
    """)

    # Put both the registration directory and the working directory on the
    # import path. A console script, unlike ``python -m``, does not add the
    # working directory itself, so component paths written relative to the
    # project root ("examples.components.Loader") would not import.
    for candidate in (directory.as_posix(), Path.cwd().as_posix()):
        if candidate not in sys.path:
            sys.path.insert(0, candidate)

    return directory, external_directories


def _log_selection(keys: List[RegistrationKey]) -> None:
    listing = os.linesep.join(f"{idx + 1}. {str(key)}" for idx, key in enumerate(keys))
    logger.info(
        f"You have selected the following keys to execute: {os.linesep}{listing}"
    )


def _prompt_for_keys(candidates: List[RegistrationKey]) -> List[RegistrationKey]:
    """
    Prompt until the user settles on a non-empty selection.

    Filters that match nothing are re-prompted; an explicit cancellation
    (``filter_keys`` returning ``None``) returns no keys so the caller aborts.
    Without that distinction, cancelling would re-open the prompt forever.
    """
    while True:
        selected = filter_keys(keys=list(candidates))
        if selected is None:
            logger.info("Selection cancelled. Aborting...")
            return []
        if len(selected):
            return selected
        logger.info("No key matched the given filters. Try again...")


def build():
    _configure_logging()
    args = _build_parser().parse_args()
    directory, external_directories = _resolve_sources(args)

    valid_keys, invalid_keys = Registry.build(
        directory=directory, external_directories=external_directories
    )
    valid_keys = sorted(valid_keys, key=lambda key: key.name)
    invalid_keys = sorted(invalid_keys, key=lambda key: key.name)

    registration_path = directory.joinpath("registrations")
    registration_path.mkdir(parents=True, exist_ok=True)

    # RegistrationKey is not JSON-serializable; its str() form round-trips
    # via RegistrationKey.from_string() (used by cmn-run / cmn-generate).
    valid_keys = [str(key) for key in valid_keys]
    invalid_keys = [str(key) for key in invalid_keys]

    with registration_path.joinpath("valid_keys.json").open("w") as f:
        json.dump(valid_keys, f)
    with registration_path.joinpath("invalid_keys.json").open("w") as f:
        json.dump(invalid_keys, f)

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
    _configure_logging()
    inquirer = _require_inquirer()

    args = _build_parser().parse_args()
    directory, external_directories = _resolve_sources(args)

    Registry.build(directory=directory, external_directories=external_directories)
    keys = Registry.retrieve_runnable_keys()

    if not len(keys):
        logger.info("Could not find any registered runnable component. Aborting...")
        return

    filtered_keys = _prompt_for_keys(keys)
    if not len(filtered_keys):
        return
    _log_selection(filtered_keys)

    if not inquirer.confirm(message="Proceed?", default=True).execute():
        return

    for key in filtered_keys:
        logger.info(f"Executing {key}")

        config_info = Registry.retrieve_configuration_info(registration_key=key)
        logger.info(config_info.config.model_dump())

        component = Registry.from_key(registration_key=key)

        assert config_info.run_method is not None
        if not hasattr(component, config_info.run_method):
            message = (
                f"Component {component} has no method {config_info.run_method}!"
                f" Aborting..."
            )
            logger.error(message)
            raise RuntimeError(message)

        getattr(component, config_info.run_method)()


def generate():
    _configure_logging()
    inquirer = _require_inquirer()

    args = _build_parser(run_directory=True, filename=True).parse_args()
    directory, external_directories = _resolve_sources(args)
    run_directory = check_directory(directory_path=args.run_directory)

    valid_keys, _ = Registry.build(
        directory=directory, external_directories=external_directories
    )

    if not len(valid_keys):
        logger.info("Could not find any registered runnable component. Aborting...")
        return

    filtered_keys = _prompt_for_keys(valid_keys)
    if not len(filtered_keys):
        return
    _log_selection(filtered_keys)

    if not inquirer.confirm(message="Proceed?", default=True).execute():
        return

    code_keys = f",{os.linesep}".join([f'"{str(key)}"' for key in filtered_keys])
    external_argument = external_directories or "None"

    code_template = f"""
# Automatically generated via cmn-generate
import logging
from logging import getLogger
from pathlib import Path
from cinnamon.registry import Registry, RegistrationKey

if __name__ == '__main__':
    Registry.build(
        directory=Path('{directory}'),
        external_directories={external_argument},
    )
    logging.basicConfig(level=logging.INFO)
    logger = getLogger(__name__)

    keys = [
        {code_keys}
]

    # RegistrationKey.from_string() rebuilds the key from its string form
    for key in keys:
        key = RegistrationKey.from_string(key)

        config_info = Registry.retrieve_configuration_info(registration_key=key)
        logger.info(config_info.config.model_dump())

        component = Registry.from_key(registration_key=key)

        if hasattr(component, config_info.run_method):
            getattr(component, config_info.run_method)()
    """

    script_path = run_directory.joinpath(f"{args.filename}.py")
    if script_path.exists():
        response = input(
            f"Script path {script_path} already exists. "
            f"Do you want to overwrite it? Y/N "
        )
        if response.strip().casefold() != "y":
            logger.info("Aborting...")
            return

    with open(script_path, "w") as f:
        f.write(code_template)


def check() -> None:
    """
    Report registration problems without running anything.

    Two passes, in the order the problems occur:

    1. **Keys** -- run after ``Registry.load`` so that *every* broken reference
    is visible. ``dag_resolution`` stops at the first one, which is why a
    project with three typos otherwise takes three runs to fix.
    2. **Bindings** -- only once the keys resolve, since the component analyzer
    needs an expanded registry.

    The binding pass resolves component paths on the filesystem without
    importing them, so the command stays fast whatever the components weigh.
    ``--deep`` imports each one to check its ``__init__`` against the
    configuration's fields, at the cost of that import.

    Exits non-zero when errors are found, so it can gate a commit or a CI job.
    """
    _configure_logging()

    args = _build_parser(strict=True).parse_args()
    directory, external_directories = _resolve_sources(args)

    Registry.load(directory=directory, external_directories=external_directories)

    findings = analyze_keys(Registry)
    print(format_findings(findings))

    errors = [
        finding
        for finding in findings
        if finding.severity is key_analyzer.Severity.ERROR
    ]
    warnings = [finding for finding in findings if finding not in errors]

    if errors:
        print(
            f"\n{len(errors)} unresolved key(s): skipping the binding analysis, "
            f"which needs a registry that resolves."
        )
        raise SystemExit(1)

    Registry.dag_resolution()

    # Only meaningful once resolution has run: the variant configurations do not
    # exist before it.
    explanations = format_variant_explanations(explain_variant_tags(Registry))
    if explanations:
        print()
        print(explanations)

    deep = getattr(args, "deep", False)
    bindings = analyze_registry(Registry, deep=deep)
    print()
    if not deep:
        print(
            "(component paths checked without importing; --deep also checks "
            "each __init__ signature)"
        )
    print_analysis_summary(bindings)

    binding_errors = sum(1 for ok_flag, _, _ in bindings.values() if not ok_flag)
    if binding_errors or (warnings and getattr(args, "strict", False)):
        raise SystemExit(1)
