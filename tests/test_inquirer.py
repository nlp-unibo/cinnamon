"""
inquirer.py prompt-selection tests.

The module binds ``InquirerPy.inquirer`` at import time, so we monkeypatch the
module-level name ``cinnamon.utility.inquirer.inquirer`` with a fake that
returns canned selections instead of touching a real terminal.
"""

from cinnamon.configuration import Configuration
from cinnamon.registry import Registry
from cinnamon.utility import inquirer as inquirer_mod


class _Execute:
    def __init__(self, value):
        self._value = value

    def execute(self):
        return self._value


class FakeInquirer:
    """Selectable fake for ``cinnamon.utility.inquirer.inquirer``.

    Selections are given as the *labels* a user would click. They are resolved
    against the offered choices and the matching ``Choice.value`` is returned,
    because that is what InquirerPy hands back -- never the display name. A
    fake that echoed the label instead would let a control option whose value
    differs from its label pass tests while being dead in production.
    """

    def __init__(self, *selections):
        self.selections = list(selections)
        self.select_calls = []
        self.checkbox_calls = []

    @staticmethod
    def _resolve(selection, choices):
        for choice in choices:
            if getattr(choice, "name", None) == selection:
                return choice.value
        # Plain string choices are their own value in InquirerPy.
        return selection

    def select(self, **kwargs):
        self.select_calls.append(kwargs)
        if not self.selections:
            raise AssertionError("Unexpected inquirer.select() call")
        return _Execute(self._resolve(self.selections.pop(0), kwargs["choices"]))

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

    assert selected is None


def test_filter_keys_tags_cancel(reset_registry, monkeypatch):
    _register("a", "ns1", tags={"t1"})
    keys = list(Registry.retrieve_keys())

    fake = FakeInquirer("a", "Cancel")
    monkeypatch.setattr(inquirer_mod, "inquirer", fake)

    selected = inquirer_mod.filter_keys(keys=keys)

    assert selected is None


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


def test_select_tags_offers_no_untagged_option(reset_registry, monkeypatch):
    """The unreachable "No Tags" choice is gone; only real controls are offered."""
    _register("a", "ns1", tags={"t1"})
    keys = list(Registry.retrieve_keys())

    fake = FakeInquirer("t1", "Proceed")
    monkeypatch.setattr(inquirer_mod, "inquirer", fake)

    inquirer_mod.select_tags(keys=keys)

    offered = [
        getattr(choice, "name", choice) for choice in fake.select_calls[0]["choices"]
    ]
    assert "No Tags" not in offered


# -- regressions --


def test_select_keys_returns_the_keys_that_were_displayed(reset_registry, monkeypatch):
    """Checkbox indices must resolve against the list that was rendered.

    Regression: choices were numbered from a name-sorted copy while the
    selection was looked up in the caller's unsorted list, so picking the first
    entry shown could return a different key entirely.
    """
    _register("zebra", "ns1")
    _register("alpha", "ns1")
    keys = [
        Registry.retrieve_keys(names="zebra")[0],
        Registry.retrieve_keys(names="alpha")[0],
    ]

    fake = FakeInquirer([0])  # the user ticks the first entry on screen
    monkeypatch.setattr(inquirer_mod, "inquirer", fake)

    selected = inquirer_mod.select_keys(keys=keys)

    displayed_first = fake.checkbox_calls[0]["choices"][0]
    assert displayed_first.value == 0
    assert "alpha" in displayed_first.name  # rendering is name-sorted
    assert [key.name for key in selected] == ["alpha"]


def test_select_name_cancel_aborts_rather_than_matching_everything(
    reset_registry, monkeypatch
):
    """Cancelling must return no keys.

    Regression: the Cancel choice carried ``value=None`` while the code
    compared against the label ``"Cancel"``, so cancelling fell through to
    ``retrieve_keys(names=None)`` -- which matches every key.
    """
    _register("a", "ns1")
    _register("b", "ns1")
    keys = list(Registry.retrieve_keys())

    fake = FakeInquirer("Cancel")
    monkeypatch.setattr(inquirer_mod, "inquirer", fake)

    name, filtered = inquirer_mod.select_name(keys=keys)

    assert name is None
    assert filtered == []


def test_select_tags_can_proceed_with_no_tag_selected(reset_registry, monkeypatch):
    """Proceed is offered even before a tag is picked, and filters nothing out."""
    _register("a", "ns1", tags={"t1"})
    _register("b", "ns1", tags={"t2"})
    keys = list(Registry.retrieve_keys())

    fake = FakeInquirer("Proceed")
    monkeypatch.setattr(inquirer_mod, "inquirer", fake)

    tags, filtered = inquirer_mod.select_tags(keys=keys)

    assert tags == []
    assert len(filtered) == 2


def test_filter_keys_returns_empty_when_name_filter_matches_nothing(
    reset_registry, monkeypatch
):
    """An empty result after the name step short-circuits the remaining prompts."""
    _register("a", "ns1")
    keys = list(Registry.retrieve_keys())

    fake = FakeInquirer("nonexistent")
    monkeypatch.setattr(inquirer_mod, "inquirer", fake)

    assert inquirer_mod.filter_keys(keys=keys) == []
    assert len(fake.select_calls) == 1  # tag prompt never reached


def test_filter_keys_returns_empty_when_tag_filter_matches_nothing(
    reset_registry, monkeypatch
):
    """An empty result after the tag step short-circuits the checkbox prompt."""
    _register("a", "ns1", tags={"t1"})
    keys = list(Registry.retrieve_keys())

    fake = FakeInquirer("a", "nonexistent-tag", "Proceed")
    monkeypatch.setattr(inquirer_mod, "inquirer", fake)

    assert inquirer_mod.filter_keys(keys=keys) == []
    assert fake.checkbox_calls == []
