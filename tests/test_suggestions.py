"""Ranking and explanation of "did you mean ...?" key suggestions."""

from cinnamon.registry import RegistrationKey
from cinnamon.utility.suggestions import (
    KeySuggestion,
    closest_string,
    describe_difference,
    similarity,
    suggest_keys,
)

NAMESPACE = "nlp"

TOKENIZER = RegistrationKey(name="tokenizer", namespace=NAMESPACE)
LOADER_IMDB = RegistrationKey(name="loader", tags={"imdb"}, namespace=NAMESPACE)
LOADER_IMDB_V2 = RegistrationKey(
    name="loader", tags={"imdb", "v2"}, namespace=NAMESPACE
)
LOADER_SST2 = RegistrationKey(name="loader", tags={"sst2"}, namespace=NAMESPACE)
MODEL = RegistrationKey(name="model", tags={"svc"}, namespace="models")

REGISTERED = [TOKENIZER, LOADER_IMDB, LOADER_IMDB_V2, LOADER_SST2, MODEL]


# -- similarity -------------------------------------------------------------


def test_similarity_ignores_case_mismatch():
    """SequenceMatcher scores 'IMDB' against 'imdb' as zero; we must not."""
    assert similarity("IMDB", "imdb") == 1.0
    assert similarity("TF-IDF", "tfidf") > 0.8


def test_similarity_still_separates_unrelated_strings():
    assert similarity("tokenizer", "pipeline") < 0.6


def test_closest_string_returns_none_when_nothing_is_close():
    assert closest_string("imbd", ["imdb", "sst2"]) == "imdb"
    assert closest_string("zzzz", ["imdb", "sst2"]) is None


# -- explanations -----------------------------------------------------------


def test_describe_difference_names_the_component_that_differs():
    target = RegistrationKey(name="tokeniser", namespace=NAMESPACE)
    assert describe_difference(target, TOKENIZER) == "name 'tokeniser' -> 'tokenizer'"


def test_describe_difference_pairs_a_misspelt_tag():
    """A near-identical tag is reported as a substitution, not add + drop."""
    target = RegistrationKey(name="loader", tags={"imbd"}, namespace=NAMESPACE)
    assert describe_difference(target, LOADER_IMDB) == "tag 'imbd' -> 'imdb'"


def test_describe_difference_reports_a_plain_omission():
    assert describe_difference(LOADER_IMDB, LOADER_IMDB_V2) == "add tags ['v2']"


def test_describe_difference_reports_namespace():
    target = RegistrationKey(name="model", tags={"svc"}, namespace=NAMESPACE)
    assert describe_difference(target, MODEL) == "namespace 'nlp' -> 'models'"


def test_describe_difference_of_an_identical_key():
    assert describe_difference(LOADER_IMDB, LOADER_IMDB) == "identical"


# -- ranking ----------------------------------------------------------------


def test_name_typo_is_the_top_suggestion():
    target = RegistrationKey(name="tokeniser", namespace=NAMESPACE)
    assert suggest_keys(target, REGISTERED)[0].key == TOKENIZER


def test_tag_typo_ranks_the_closest_tag_set_first():
    target = RegistrationKey(name="loader", tags={"imbd"}, namespace=NAMESPACE)
    ranked = suggest_keys(target, REGISTERED)

    assert ranked[0].key == LOADER_IMDB
    assert ranked[0].reason == "tag 'imbd' -> 'imdb'"
    # every same-name key is offered, ordered by closeness
    assert [suggestion.key for suggestion in ranked] == [
        LOADER_IMDB,
        LOADER_IMDB_V2,
        LOADER_SST2,
    ]


def test_unrelated_names_are_not_suggested():
    """Namespace and tag agreement must not carry an unrelated name."""
    target = RegistrationKey(name="tokeniser", namespace=NAMESPACE)
    suggested = {suggestion.key.name for suggestion in suggest_keys(target, REGISTERED)}

    assert suggested == {"tokenizer"}


def test_nothing_similar_yields_no_suggestion():
    target = RegistrationKey(name="zzzzzz", namespace="qqq")
    assert suggest_keys(target, REGISTERED) == []


def test_the_key_itself_is_never_suggested():
    assert all(
        suggestion.key != LOADER_IMDB
        for suggestion in suggest_keys(LOADER_IMDB, REGISTERED)
    )


def test_suggestion_limit_is_honoured():
    target = RegistrationKey(name="loader", tags={"imbd"}, namespace=NAMESPACE)
    assert len(suggest_keys(target, REGISTERED, limit=1)) == 1


def test_suggestion_renders_key_and_reason():
    suggestion = KeySuggestion(key=TOKENIZER, score=0.9, reason="name differs")
    assert str(suggestion) == f"{TOKENIZER} (name differs)"


def test_a_similar_name_alone_is_not_enough():
    """The name veto lets a candidate through; the overall score still gates it."""
    target = RegistrationKey(name="loader", tags={"x"}, namespace="aaa")
    candidate = RegistrationKey(name="loaded", tags={"y"}, namespace="zzz")

    assert similarity("loader", "loaded") > 0.6  # passes the name veto
    assert suggest_keys(target, [candidate]) == []  # but not the score threshold
