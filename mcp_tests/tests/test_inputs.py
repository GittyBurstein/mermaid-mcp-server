import pytest

from core.errors import ValidationError
from clients.github.inputs import (
    parse_repo_url,
    normalize_ref,
    normalize_path,
    normalize_max_chars,
)


def test_parse_repo_url_valid_variants():
    assert parse_repo_url("https://github.com/octocat/Hello-World") == ("octocat", "Hello-World")
    assert parse_repo_url("https://github.com/octocat/Hello-World/") == ("octocat", "Hello-World")
    assert parse_repo_url("https://github.com/octocat/Hello-World.git") == ("octocat", "Hello-World")


def test_parse_repo_url_invalid():
    with pytest.raises(ValidationError):
        parse_repo_url("not a url")
    with pytest.raises(ValidationError):
        parse_repo_url("https://gitlab.com/a/b")


def test_normalize_ref():
    assert normalize_ref(None) == "main"
    assert normalize_ref(" main ") == "main"
    with pytest.raises(ValidationError):
        normalize_ref("   ")


def test_normalize_path():
    assert normalize_path(" /src/app.py ") == "src/app.py"
    assert normalize_path("/src/app.py") == "src/app.py"
    with pytest.raises(ValidationError):
        normalize_path("")
    with pytest.raises(ValidationError):
        normalize_path("   ")
    with pytest.raises(ValidationError):
        normalize_path("/")


def test_normalize_max_chars():
    assert normalize_max_chars(10) == 10
    assert normalize_max_chars("12") == 12
    with pytest.raises(ValidationError):
        normalize_max_chars(0)
    with pytest.raises(ValidationError):
        normalize_max_chars(-5)
