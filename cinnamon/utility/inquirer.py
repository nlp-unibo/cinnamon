from typing import List

from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from InquirerPy.separator import Separator
from copy import deepcopy

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
    keys = select_keys(keys=keys, selected_tags=selected_tags)

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


def select_tags(
        keys: List[cinnamon.registry.RegistrationKey]
):
    selected_tags = []
    current_tag = None
    current_keys = deepcopy(keys)
    while current_tag != "Proceed":
        tags = set()
        for key in current_keys:
            tags = tags.union(key.tags)
        tags = tags.difference(set(selected_tags))

        add_no_tag = None in selected_tags
        add_go_back = len(selected_tags) > 0

        choices = [Choice(value='Cancel', name='Cancel')]
        if add_no_tag:
            choices.insert(0, Choice(value=None, name='No Tags'))
        if add_go_back:
            choices.insert(0, Choice(value='Go back', name='Go back'))

        if len(selected_tags):
            choices.insert(0, Choice(value='Proceed', name='Proceed'))

        choices.append(Separator())

        choices += sorted(list(tags))

        current_tag = inquirer.select(
            message=f'Select a tag (total = {len(tags)}) \nCurrent selection: {selected_tags}',
            choices=choices,
            default=None,
            mandatory=True
        ).execute()

        if current_tag == 'Cancel':
            return None, []

        if current_tag == 'Go back':
            selected_tags.pop(-1)
            continue

        if current_tag == 'Proceed':
            break

        selected_tags.append(current_tag)
        current_keys = cinnamon.registry.Registry.retrieve_keys(tags=set(selected_tags),
                                                                keys=keys)

    return selected_tags, current_keys


def select_keys(
        keys: List[cinnamon.registry.RegistrationKey],
        selected_tags: cinnamon.registry.Tags = None
):
    selected_tags = selected_tags if selected_tags is not None else {}

    selected_indexes = inquirer.checkbox(
        message=f'Select one or more keys to execute (total = {len(keys)}) \nSelected tags: {selected_tags}',
        choices=[Choice(name=f"{idx + 1}. {key.from_tags_simplification(tags=selected_tags).to_pretty_string()}",
                        value=idx)
                 for idx, key in enumerate(sorted(keys, key=lambda item: item.name))],
        validate=lambda result: len(result) >= 1,
        transformer=lambda result: f'{len(result)} selected.',
        instruction='(select at least one key)',
        mandatory=True
    ).execute()

    selected_keys = [key for idx, key in enumerate(keys) if idx in selected_indexes]

    return selected_keys
