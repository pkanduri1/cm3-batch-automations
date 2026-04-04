# tests/unit/test_downloader_service.py
import io
import tarfile
import zipfile
import pytest
from pathlib import Path
from src.services.downloader_service import validate_path, browse_path, BrowseEntry


def test_validate_path_accepts_allowed(tmp_path):
    assert validate_path(str(tmp_path), [str(tmp_path)]) == tmp_path.resolve()


def test_validate_path_accepts_subpath(tmp_path):
    sub = tmp_path / "sub"
    sub.mkdir()
    assert validate_path(str(sub), [str(tmp_path)]) == sub.resolve()


def test_validate_path_rejects_traversal(tmp_path):
    with pytest.raises(ValueError, match="not within any configured"):
        validate_path(str(tmp_path), [str(tmp_path / "safe")])


def test_validate_path_rejects_unlisted(tmp_path):
    other = tmp_path / "other"
    other.mkdir()
    with pytest.raises(ValueError):
        validate_path(str(other), [str(tmp_path / "safe")])


def test_browse_lists_plain_files(tmp_path):
    (tmp_path / "report.csv").write_text("a,b")
    entries = browse_path(tmp_path)
    assert any(e.name == "report.csv" and e.type == "plain" for e in entries)


def test_browse_identifies_archives(tmp_path):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        data = b"x"
        info = tarfile.TarInfo(name="f.txt")
        info.size = len(data)
        tf.addfile(info, io.BytesIO(data))
    (tmp_path / "a.tar.gz").write_bytes(buf.getvalue())
    with zipfile.ZipFile(tmp_path / "b.zip", "w") as zf:
        zf.writestr("f.txt", "x")
    buf2 = io.BytesIO()
    with tarfile.open(fileobj=buf2, mode="w:gz") as tf:
        data2 = b"y"
        info2 = tarfile.TarInfo(name="g.txt")
        info2.size = len(data2)
        tf.addfile(info2, io.BytesIO(data2))
    (tmp_path / "c.tgz").write_bytes(buf2.getvalue())
    types = {e.name: e.type for e in browse_path(tmp_path)}
    assert types["a.tar.gz"] == "archive"
    assert types["b.zip"] == "archive"
    assert types["c.tgz"] == "archive"


def test_browse_wildcard_filter(tmp_path):
    (tmp_path / "batch_01.tar.gz").write_bytes(b"x")
    (tmp_path / "unrelated.txt").write_text("x")
    names = [e.name for e in browse_path(tmp_path, pattern="batch_*.tar.gz")]
    assert "batch_01.tar.gz" in names
    assert "unrelated.txt" not in names


def test_browse_returns_size(tmp_path):
    (tmp_path / "f.txt").write_text("hello")
    entry = next(e for e in browse_path(tmp_path) if e.name == "f.txt")
    assert entry.size_bytes == 5
