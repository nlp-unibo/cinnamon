"""
inquirer.py prompt-selection tests.

The module binds ``InquirerPy.inquirer`` at import time, so we monkeypatch the
module-level name ``cinnamon.utility.inquirer.inquirer`` with a fake that
returns canned selections instead of touching a real terminal.
"""

import pytest

from cinnamon.configuration import Configuration
from cinnamon.registry import Registry
from cinnamon.utility import inquirer as inquirer_mod
from tests.fixtures import reset_registry


class _Execute:
    def __init__(self, value):
        self._value = value

    def execute(self):
        return self._value


class FakeInquirer:
    """Selectable fake for ``cinnamon.utility.inquirer.inquirer``."""

    def __init__(self, *selections):
        self.selections = list(selections)
        self.select_calls = []
        self.checkbox_calls = []

    def select(self, **kwargs):
        self.select_calls.append(kwargs)
        if not self.selections:
            raise AssertionError("Unexpected inquirer.select() call")
        return _Execute(self.selections.pop(0))

    def checkbox(self, **kwargs):
        self.checkbox_calls.append(kwargs)
        if not self.selections:
            raise AssertionError("Unexpected inquirer.checkbox() call")
        return _Execute(self.selections.pop(0))


def _register(name, namespace, tags=None):
    return Registry.register_configuration(
        config=Configuration.default(),
        name=name,
        namespace=namespace,
        tags=tags,
    )


# -- select_namespace --


def test_select_namespace_single_no_prompt(reset_registry, monkeypatch):
    _register("a", "ns1")
    _register("b", "ns1")
    keys = list(Registry.retrieve_keys())

    fake = FakeInquirer()
    monkeypatch.setattr(inquirer_mod, "inquirer", fake)

    namespace, filtered = inquirer_mod.select_namespace(keys=keys)

    assert namespace == "ns1"
    assert len(fake.select_calls) == 0  # single namespace => no prompt
    assert len(filtered) == 2


def test_select_namespace_multiple_prompts(reset_registry, monkeypatch):
    _register("a", "ns1")
    _register("b", "ns2")
    keys = list(Registry.retrieve_keys())

    fake = FakeInquirer("ns2")
    monkeypatch.setattr(inquirer_mod, "inquirer", fake)

    ns, filtered = inquirer_mod.select_namespace(keys=keys)

    assert ns == "ns2"
    assert len(fake.select_calls) == 1
    assert all(k.namespace == "ns2" for k in filtered)


# -- select_name --


def test_select_name_cancel(reset_registry, monkeypatch):
    _register("a", "ns1")
    keys = list(Registry.retrieve_keys())

    fake = FakeInquirer("Cancel")
    monkeypatch.setattr(inquirer_mod, "inquirer", fake)

    name, filtered = inquirer_mod.select_name(keys=keys)

    assert name is None
    assert filtered == []


def test_select_name_selection(reset_registry, monkeypatch):
    _register("a", "ns1")
    _register("b", "ns1")
    keys = list(Registry.retrieve_keys())

    fake = FakeInquirer("b")
    monkeypatch.setattr(inquirer_mod, "inquirer", fake)

    name, filtered = inquirer_mod.select_name(keys=keys)

    assert name == "b"
    assert len(filtered) == 1
    assert filtered[0].name == "b"


# -- select_tags --


def test_select_tags_proceed(reset_registry, monkeypatch):
    _register("a", "ns1", tags={"t1"})
    keys = list(Registry.retrieve_keys())

    fake = FakeInquirer("t1", "Proceed")
    monkeypatch.setattr(inquirer_mod, "inquirer", fake)

    tags, filtered = inquirer_mod.select_tags(keys=keys)

    assert tags == ["t1"]
    assert len(filtered) == 1


# -- select_keys --


def test_select_keys_checkbox(reset_registry, monkeypatch):
    _register("a", "ns1")
    _register("b", "ns1")
    keys = sorted(list(Registry.retrieve_keys()), key=lambda k: k.name)

    fake = FakeInquirer([0])
    monkeypatch.setattr(inquirer_mod, "inquirer", fake)

    selected = inquirer_mod.select_keys(keys=keys, selected_tags=None)

    assert selected == [keys[0]]


# -- filter_keys end-to-end --


def test_filter_keys_full_flow(reset_registry, monkeypatch):
    _register("a", "ns1", tags={"t1"})
    keys = list(Registry.retrieve_keys())

    # select_namespace: single ns => no prompt.
    # select_name -> "a", select_tags -> t1 then Proceed, select_keys -> index 0
    fake = FakeInquirer("a", "t1", "Proceed", [0])
    monkeypatch.setattr(inquirer_mod, "inquirer", fake)

    selected = inquirer_mod.filter_keys(keys=keys)

    assert len(selected) == 1
    assert selected[0].name == "a"


def test_filter_keys_namespace_filter_empty(reset_registry, monkeypatch):
    # Two namespaces so select_namespace prompts; fake returns an unknown one.
    _register("a", "ns1")
    _register("b", "ns2")
    keys = list(Registry.retrieve_keys())

    fake = FakeInquirer("ns_other")
    monkeypatch.setattr(inquirer_mod, "inquirer", fake)

    selected = inquirer_mod.filter_keys(keys=keys)

    assert selected == []


def test_filter_keys_name_cancel(reset_registry, monkeypatch):
    _register("a", "ns1")
    keys = list(Registry.retrieve_keys())

    fake = FakeInquirer("Cancel")
    monkeypatch.setattr(inquirer_mod, "inquirer", fake)

    selected = inquirer_mod.filter_keys(keys=keys)

    assert selected == []


def test_filter_keys_tags_cancel(reset_registry, monkeypatch):
    _register("a", "ns1", tags={"t1"})
    keys = list(Registry.retrieve_keys())

    fake = FakeInquirer("a", "Cancel")
    monkeypatch.setattr(inquirer_mod, "inquirer", fake)

    selected = inquirer_mod.filter_keys(keys=keys)

    assert selected == []


def test_select_tags_cancel(reset_registry, monkeypatch):
    _register("a", "ns1", tags={"t1"})
    keys = list(Registry.retrieve_keys())

    fake = FakeInquirer("Cancel")
    monkeypatch.setattr(inquirer_mod, "inquirer", fake)

    tags, filtered = inquirer_mod.select_tags(keys=keys)

    assert tags is None
    assert filtered == []


def test_select_tags_go_back(reset_registry, monkeypatch):
    _register("a", "ns1", tags={"t1"})
    keys = list(Registry.retrieve_keys())

    fake = FakeInquirer("t1", "Go back", "Proceed")
    monkeypatch.setattr(inquirer_mod, "inquirer", fake)

    tags, filtered = inquirer_mod.select_tags(keys=keys)

    assert tags == []


def test_select_tags_no_tags_option(reset_registry, monkeypatch):
    _register("a", "ns1", tags={"t1"})
    keys = list(Registry.retrieve_keys())

    fake = FakeInquirer(None, "Proceed")
    monkeypatch.setattr(inquirer_mod, "inquirer", fake)

    tags, filtered = inquirer_mod.select_tags(keys=keys)

    assert tags == [None]
    assert len(filtered) == 1
