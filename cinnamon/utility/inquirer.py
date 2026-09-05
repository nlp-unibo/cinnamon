from copy import deepcopy
from typing import Any, List, Optional

from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from InquirerPy.separator import Separator

import cinnamon.registry

# Sentinels returned as Choice *values*. InquirerPy hands back the value of the
# selected choice, never its display name, so control options must be
# distinguished by value -- comparing against the label silently never matches.
CANCEL = "__cancel__"
GO_BACK = "__go_back__"
PROCEED = "__proceed__"

__all__ = [
    "filter_keys",
    "select_namespace",
    "select_name",
    "select_tags",
    "select_keys",
]


def filter_keys(
    keys: List["cinnamon.registry.RegistrationKey"],
) -> Optional[List["cinnamon.registry.RegistrationKey"]]:
    """
    Narrow *keys* down interactively by namespace, then name, then tags.

    Returns:
        The selected keys, ``[]`` if the filters matched nothing, or ``None``
        if the user cancelled. The caller must distinguish the last two: an
        empty match is worth re-prompting, a cancellation is not.
    """
    keys = sorted(keys, key=str)
    selected_namespace, keys = select_namespace(keys=keys)
    if not len(keys):
        return keys

    keys = sorted(keys, key=str)
    selected_name, keys = select_name(keys=keys)
    if selected_name is None:
        return None
    if not len(keys):
        return keys

    keys = sorted(keys, key=str)
    selected_tags, keys = select_tags(keys=keys)
    if selected_tags is None:
        return None
    if not len(keys):
        return keys

    keys = sorted(keys, key=str)
    keys = select_keys(keys=keys, selected_tags=selected_tags)

    return sorted(keys, key=str)


def select_namespace(keys: List["cinnamon.registry.RegistrationKey"]):
    namespaces = set([key.namespace for key in keys])

    # Namespace
    if len(namespaces) > 1:
        selected_namespace = inquirer.select(
            message=f"Select a namespace (total = {len(namespaces)})",
            choices=sorted(list(namespaces)),
            mandatory=True,
        ).execute()
    else:
        selected_namespace = namespaces.pop()

    keys = cinnamon.registry.Registry.retrieve_keys(
        namespaces=selected_namespace, keys=keys
    )

    return selected_namespace, keys


def select_name(keys: List["cinnamon.registry.RegistrationKey"]):
    # Name
    names = set([key.name for key in keys])

    selected_name = inquirer.select(
        message=f"Select a name (total = {len(names)})",
        choices=[Choice(value=CANCEL, name="Cancel"), Separator()]
        + sorted(list(names)),
        mandatory=True,
    ).execute()

    if selected_name == CANCEL:
        return None, []

    keys = cinnamon.registry.Registry.retrieve_keys(names=selected_name, keys=keys)

    return selected_name, keys


def select_tags(keys: List["cinnamon.registry.RegistrationKey"]):
    selected_tags: List[str] = []
    current_keys = deepcopy(keys)
    while True:
        tags: set = set()
        for key in current_keys:
            tags = tags.union(key.tags)
        tags = tags.difference(set(selected_tags))

        # NOTE: a "No Tags" choice used to be offered here, gated on
        # ``None in selected_tags`` -- a condition that could only become true
        # after the choice had already been picked, so it was never reachable.
        # It is left out rather than revived: match_tags() treats a ``None``
        # entry as a wildcard that also admits *tagged* keys, so an untagged
        # filter needs its semantics settled before it means anything.
        add_go_back = len(selected_tags) > 0

        choices: List[Any] = [Choice(value=CANCEL, name="Cancel")]
        if add_go_back:
            choices.insert(0, Choice(value=GO_BACK, name="Go back"))

        # Always offered: with no tags picked it means "do not filter by tag".
        # Gating it on a non-empty selection stranded anyone who backed out of
        # their last tag -- their only remaining option was to cancel.
        choices.insert(0, Choice(value=PROCEED, name="Proceed"))

        choices.append(Separator())

        choices += sorted(list(tags))

        current_tag = inquirer.select(
            message=f"Select a tag (total = {len(tags)}) "
            f"\nCurrent selection: {selected_tags}",
            choices=choices,
            default=None,
            mandatory=True,
        ).execute()

        if current_tag == CANCEL:
            return None, []

        if current_tag == GO_BACK:
            selected_tags.pop(-1)
            continue

        if current_tag == PROCEED:
            break

        selected_tags.append(current_tag)
        current_keys = cinnamon.registry.Registry.retrieve_keys(
            tags=set(selected_tags), keys=keys
        )

    return selected_tags, current_keys


def select_keys(
    keys: List["cinnamon.registry.RegistrationKey"],
    selected_tags: "cinnamon.registry.Tags" = None,
) -> List["cinnamon.registry.RegistrationKey"]:
    selected_tags = selected_tags if selected_tags is not None else set()

    # Choice values index into `ordered`, so the returned keys must be looked up
    # in that same list -- indexing back into `keys` returns the wrong entries
    # whenever the two orders differ.
    ordered = sorted(keys, key=lambda item: item.name)

    selected_indexes = inquirer.checkbox(
        message=f"Select one or more keys to execute (total = {len(ordered)})"
        f" \nSelected tags: {selected_tags}",
        choices=[
            Choice(
                name=f"{idx + 1}. "
                f"{key.from_tags_simplification(tags=selected_tags).to_pretty_string()}",
                value=idx,
            )
            for idx, key in enumerate(ordered)
        ],
        validate=lambda result: len(result) >= 1,
        transformer=lambda result: f"{len(result)} selected.",
        instruction="(select at least one key)",
        mandatory=True,
    ).execute()

    return [ordered[idx] for idx in selected_indexes]
