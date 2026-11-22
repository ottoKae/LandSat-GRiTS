"""Assert that a release includes runtime assets and excludes private pilot data."""
import argparse
from pathlib import Path
import re
import tarfile
import zipfile


def check_public_text(name, data):
    text = data.decode("utf-8", errors="replace")
    private = re.search(
        r"(?i)(?:[A-Z]:[\\/]+(?:Users|Project|QGIS)[\\/]+|/(?:home|Users)/[^/\s]+/)",
        text,
    )
    credential = re.search(
        r"(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,}|"
        r"AKIA[A-Z0-9]{16}|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----)",
        text,
    )
    emails = re.findall(r"[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})", text)
    personal_email = any(
        domain.lower() not in {
            "example.com", "example.org", "example.net", "users.noreply.github.com",
        } and not domain.lower().endswith((".invalid", ".test"))
        for domain in emails
    )
    assert not (private or credential or personal_email), f"Review private content in {name}"


def check(root):
    wheels, sources = list(root.glob("*.whl")), list(root.glob("*.tar.gz"))
    assert len(wheels) == len(sources) == 1, "Use a directory containing exactly one release"
    with zipfile.ZipFile(wheels[0]) as archive:
        names = archive.namelist()
        assert all(f"landsat_grits/web/{name}" in names for name in ("app.js", "style.css", "index.html"))
        assert any(name.endswith("/licenses/LICENSE") for name in names)
        assert "landsat_grits/grid_source.py" in names
        for name in names:
            check_public_text(name, archive.read(name))
    with tarfile.open(sources[0]) as archive:
        names = [name.split("/", 1)[-1] for name in archive.getnames()]
        for required in ("LICENSE", "NOTICE.md", "examples/offline_demo.py",
                         "tests/test_offline_demo.py", "tooling/release/smoke_installed.py",
                         "docs/USAGE.md", "tooling/validation/download.py",
                         "tooling/validation/prepare_pilot.py",
                         "tooling/validation/verify_full_tile.py",
                         "tooling/validation/append_second_path.py"):
            assert required in names, required
        assert not any(name.startswith(("outputs/", "data/", "logs/", "docs/evidence/",
                                        "config/pilots/", "tooling/diagnostics/",
                                        ".venv/", ".test-tmp/"))
                       or name.endswith(".log") for name in names)
        for member in archive.getmembers():
            if member.isfile():
                check_public_text(member.name, archive.extractfile(member).read())
    print("Release content checks passed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    check(parser.parse_args().directory)
