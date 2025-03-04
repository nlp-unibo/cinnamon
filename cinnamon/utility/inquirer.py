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
            message=f'Select a namespace (total = {len(namespaces)})',
            choices=sorted(list(namespaces)),
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
        message=f'Select a name (total = {len(names)})',
        choices=[Choice(value=None, name='Cancel'), Separator()] + sorted(list(names)),
        mandatory=True
    ).execute()

    if selected_name == 'Cancel':
        return None, []

    keys = cinnamon.registry.Registry.retrieve_keys(names=selected_name,
                                                    keys=keys)

    return selected_name, keys


# TODO: rather than a checkbox, this should be a while loop until satisfaction of selection
# After each selection we filter keys to find remaining compatible keys
# This avoids selecting combination of keys that lead to an empty set of runnable keys
def select_tags(
        keys: List[cinnamon.registry.RegistrationKey]
):
    # Tags
    tags = set()
    for key in keys:
        tags = tags.union(key.tags)

    selected_tags = inquirer.checkbox(
        message=f'Select one or more tags (total = {len(tags)})',
        choices=[Choice(value=None, name='No Tags'), Choice(value=None, name='Cancel'), Separator()] + sorted(list(tags)),
        default=None,
        mandatory=True,
        validate=lambda result: len(result) >= 1,
        instruction='(select at least one key)'
    ).execute()
    selected_tags = set(selected_tags)

    if 'Cancel' in selected_tags:
        return None, []

    if 'No Tags' in selected_tags:
        selected_tags = {None}

    keys = cinnamon.registry.Registry.retrieve_keys(tags=selected_tags,
                                                    keys=keys)

    return selected_tags, keys


# TODO: we may want to remove previously selected tags from keys to ease reading
def select_keys(
        keys: List[cinnamon.registry.RegistrationKey]
):
    selected_keys = inquirer.checkbox(
        message=f'Select one or more keys to execute (total = {len(keys)})',
        choices=sorted(keys, key=lambda item: item.name),
        validate=lambda result: len(result) >= 1,
        transformer=lambda result: f'{len(result)} selected.',
        instruction='(select at least one key)',
        mandatory=True
    ).execute()

    return selected_keys
