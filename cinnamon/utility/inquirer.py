from typing import List

from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from InquirerPy.separator import Separator

import cinnamon.registry


def filter_keys(
        keys: List[cinnamon.registry.RegistrationKey]
):
    # Namespace
    selected_namespace, keys = select_namespace(keys=keys)

    if not len(keys):
        return keys

    # Name
    selected_name, keys = select_name(keys=keys)

    if not len(keys):
        return keys

    # Tags
    selected_tags, keys = select_tags(keys=keys)

    if not len(keys):
        return keys

    # Final selection
    keys = select_keys(keys=keys)

    return keys


def select_namespace(
        keys: List[cinnamon.registry.RegistrationKey]
):
    namespaces = set([key.namespace for key in keys])

    # Namespace
    if len(namespaces) > 1:
        selected_namespace = inquirer.select(
            message='Select a namespace',
            choices=list(namespaces),
            mandatory=True
        ).execute()
    else:
        selected_namespace = namespaces.pop()

    keys = cinnamon.registry.Registry.retrieve_keys(namespaces=selected_namespace,
                                                    keys=keys)

    return selected_namespace, keys


def select_name(
        keys: List[cinnamon.registry.RegistrationKey]
):
    # Name
    names = set([key.name for key in keys])

    selected_name = inquirer.select(
        message='Select a name',
        choices=[Choice(value=None, name='Cancel'), Separator()] + list(names),
        mandatory=True
    ).execute()

    if selected_name == 'Cancel':
        return None, []

    keys = cinnamon.registry.Registry.retrieve_keys(names=selected_name,
                                                    keys=keys)

    return selected_name, keys


def select_tags(
        keys: List[cinnamon.registry.RegistrationKey]
):
    # Tags
    tags = set()
    for key in keys:
        tags = tags.union(key.tags)

    selected_tags = inquirer.select(
        message='Select one or more tags',
        choices=[Choice(value=None, name='No Tags'), Choice(value=None, name='Cancel'), Separator()] + list(tags),
        default=None,
        multiselect=True,
        mandatory=True
    ).execute()

    if selected_tags == 'Cancel':
        return None, []

    if selected_tags == 'No Tags':
        selected_tags = {None}

    keys = cinnamon.registry.Registry.retrieve_keys(tags=selected_tags,
                                                    keys=keys)

    return selected_tags, keys


def select_keys(
        keys: List[cinnamon.registry.RegistrationKey]
):
    selected_keys = inquirer.checkbox(
        message='Select one or more keys to execute',
        choices=keys,
        validate=lambda result: len(result) >= 1,
        transformer=lambda result: f'{len(result)} selected.',
        instruction='(select at least one key)',
        mandatory=True
    ).execute()

    return selected_keys
