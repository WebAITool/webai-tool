from pathlib import Path


def test_copy_fixture_to_ignored_data(copy_fixture_to_data):
    copied = copy_fixture_to_data("sample_project")

    assert copied.name == "sample_project"
    assert copied.parts[-3:] == ("tests", "data", "sample_project")
    assert (copied / "app.py").read_text(encoding="utf-8") == (
        'def hello() -> str:\n    return "hello"\n'
    )
    assert Path("tests/fixtures/sample_project/app.py").exists()
