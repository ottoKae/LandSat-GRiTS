"""Exercise the release checker against real archive members, without private data."""
import importlib.util
from pathlib import Path
import tarfile
import zipfile

import pytest


spec = importlib.util.spec_from_file_location(
    "check_artifacts", Path(__file__).parents[1] / "tooling/release/check_artifacts.py"
)
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


@pytest.mark.parametrize("content", [
    "C:/" + "Users/example/private",
    "D:" + "/Project/example/run",
    "/home/" + "example/private",
    "ghp_" + "A" * 36,
    "private.person" + "@mail.example.edu",
])
def test_release_text_rejects_private_content(content):
    with pytest.raises(AssertionError, match="Review private content"):
        checker.check_public_text("example.txt", content.encode())


def test_release_text_accepts_public_examples():
    checker.check_public_text(
        "example.txt",
        b"user@example.org ottoKae@users.noreply.github.com https://example.org?sig=fake",
    )


@pytest.mark.parametrize("kind", ["wheel", "sdist"])
def test_artifact_checker_reads_member_contents(tmp_path, kind):
    source = Path(__file__).parents[1]
    wheel = tmp_path / "example.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        for name in ("web/app.js", "web/style.css", "web/index.html", "grid_source.py"):
            archive.writestr("landsat_grits/" + name, "public fixture")
        archive.writestr("example.dist-info/licenses/LICENSE", "public fixture")
        if kind == "wheel":
            archive.writestr("landsat_grits/private.txt", "C:/" + "Users/example/private")
    with tarfile.open(tmp_path / "example.tar.gz", "w:gz") as archive:
        for name in (
            "LICENSE", "NOTICE.md", "examples/offline_demo.py", "tests/test_offline_demo.py",
            "tooling/release/smoke_installed.py", "docs/USAGE.md", "tooling/validation/download.py",
            "tooling/validation/prepare_pilot.py", "tooling/validation/verify_full_tile.py",
            "tooling/validation/append_second_path.py",
        ):
            archive.add(source / name, arcname="example/" + name)
        if kind == "sdist":
            private = tmp_path / "private.txt"
            private.write_text("C:/" + "Users/example/private", encoding="utf-8")
            archive.add(private, arcname="example/docs/private.txt")
    with pytest.raises(AssertionError, match="Review private content"):
        checker.check(tmp_path)
