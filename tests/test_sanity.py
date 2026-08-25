"""
sanity.py tests: check_directory, check_external_json_path, time_it.
"""

import json

import pytest

from cinnamon.utility.sanity import (
    check_directory,
    check_external_json_path,
    time_it,
)

# -- check_directory --


def test_check_directory_existing_dir(tmp_path):
    """Test test check directory existing dir."""
    assert check_directory(tmp_path) == tmp_path.resolve()


def test_check_directory_default_to_cwd(monkeypatch, tmp_path):
    """Test test check directory default to cwd."""
    monkeypatch.chdir(tmp_path)
    assert check_directory() == tmp_path.resolve()


def test_check_directory_missing_raises():
    """Test test check directory missing raises."""
    with pytest.raises(FileNotFoundError):
        check_directory("/nonexistent/cinnamon-dir")


def test_check_directory_file_not_dir(tmp_path):
    """Test test check directory file not dir."""
    f = tmp_path / "a_file.txt"
    f.write_text("x")
    with pytest.raises(NotADirectoryError):
        check_directory(f)


# -- check_external_json_path --


def test_check_external_json_path_valid(tmp_path):
    """Test test check external json path valid."""
    payload = [{"extension": "/tmp/ext_repo"}]
    conf = tmp_path / "externals.json"
    conf.write_text(json.dumps(payload))

    assert check_external_json_path(conf) == payload


def test_check_external_json_path_missing():
    """Test test check external json path missing."""
    with pytest.raises(FileNotFoundError):
        check_external_json_path("/nonexistent/externals.json")


def test_check_external_json_path_wrong_suffix(tmp_path):
    """Test test check external json path wrong suffix."""
    not_json = tmp_path / "externals.txt"
    not_json.write_text("[]")
    with pytest.raises(TypeError):
        check_external_json_path(not_json)


def test_check_external_json_path_invalid_json(tmp_path):
    """Test test check external json path invalid json."""
    bad = tmp_path / "externals.json"
    bad.write_text("this is not json")
    with pytest.raises(json.JSONDecodeError):
        check_external_json_path(bad)


# -- time_it --


def test_time_it_decorator():
    """Test test time it decorator."""
    calls = []

    @time_it
    def target():
        calls.append(1)
        return 42

    assert target() == 42
    assert len(calls) == 1
    # identity preserved so introspection/logging still see the real name
    assert target.__name__ == "target"
    assert hasattr(target, "__wrapped__")


def test_time_it_forwards_args():
    """Test test time it forwards args."""
    received = {}

    @time_it
    def target(x, y=None):
        received["x"] = x
        received["y"] = y
        return x

    assert target(1, y=2) == 1
    assert received == {"x": 1, "y": 2}
