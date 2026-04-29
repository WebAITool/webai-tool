import shutil
from collections.abc import Callable
from pathlib import Path

import pytest


@pytest.fixture
def generated_test_data(request: pytest.FixtureRequest) -> Path:
    data_dir = Path(request.config.rootpath) / "tests" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


@pytest.fixture
def copy_fixture_to_data(
    generated_test_data: Path,
) -> Callable[[str, str | None], Path]:
    fixtures_dir = Path(__file__).parent / "fixtures"

    def copy_fixture(name: str, dest_name: str | None = None) -> Path:
        src = fixtures_dir / name
        if not src.exists():
            raise FileNotFoundError(f"Test fixture does not exist: {src}")

        dest = generated_test_data / (dest_name or src.name)
        if dest.exists():
            if dest.is_dir():
                shutil.rmtree(dest)
            else:
                dest.unlink()

        if src.is_dir():
            shutil.copytree(src, dest)
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
        return dest

    return copy_fixture
