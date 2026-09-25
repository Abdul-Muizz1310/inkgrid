import importlib.metadata
import io
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

import pdf_factory
from inkgrid.cli import main
from inkgrid.model.document import Document
from inkgrid.model.page import Reading


def write_pdf(tmp_path: Path, data: bytes, name: str = "in.pdf") -> Path:
    path = tmp_path / name
    path.write_bytes(data)
    return path


@pytest.mark.parametrize("make", pdf_factory.OPENABLE.values(), ids=pdf_factory.OPENABLE.keys())
def test_L1_words_prints_a_valid_reading_for_every_fixture(
    make: Callable[[], bytes], tmp_path: Path, capsysbinary: pytest.CaptureFixture[bytes]
) -> None:
    path = write_pdf(tmp_path, make())
    assert main(["words", str(path)]) == 0
    out, err = capsysbinary.readouterr()
    assert err == b""
    reading = Reading.model_validate_json(out)
    assert reading.source.file_name == "in.pdf"


def test_L2_output_file_holds_canonical_json(
    tmp_path: Path, capsysbinary: pytest.CaptureFixture[bytes]
) -> None:
    path = write_pdf(tmp_path, pdf_factory.simple_text())
    target = tmp_path / "out.json"
    assert main(["words", str(path), "-o", str(target)]) == 0
    assert capsysbinary.readouterr() == (b"", b"")
    reading = Reading.model_validate_json(target.read_bytes())
    assert target.read_bytes() == reading.model_dump_json().encode() + b"\n"


def test_L3_pretty_is_indented_and_equivalent(
    tmp_path: Path, capsysbinary: pytest.CaptureFixture[bytes]
) -> None:
    path = write_pdf(tmp_path, pdf_factory.simple_text())
    assert main(["words", str(path), "--pretty"]) == 0
    pretty = capsysbinary.readouterr().out
    assert b'\n  "schema": "inkgrid.reading/1"' in pretty
    assert main(["words", str(path)]) == 0
    compact = capsysbinary.readouterr().out
    assert Reading.model_validate_json(pretty) == Reading.model_validate_json(compact)


@pytest.mark.parametrize("case", ["missing", "not-pdf"])
def test_L4_unreadable_input_exits_2_with_one_line(
    case: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "absent.pdf" if case == "missing" else write_pdf(tmp_path, b"hello")
    assert main(["words", str(path)]) == 2
    out, err = capsys.readouterr()
    assert out == ""
    assert err.startswith("inkgrid: ")
    assert err.count("\n") == 1
    assert "Traceback" not in err


def test_L5_encrypted_without_password_exits_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = write_pdf(tmp_path, pdf_factory.encrypted(user_pw="u"))
    assert main(["words", str(path)]) == 2
    assert "password" in capsys.readouterr().err


@pytest.mark.parametrize(("line", "code"), [("u\n", 0), ("nope\n", 2)])
def test_L6_password_from_stdin(
    line: str, code: int, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = write_pdf(tmp_path, pdf_factory.encrypted(user_pw="u"))
    monkeypatch.setattr(sys, "stdin", io.StringIO(line))
    monkeypatch.setattr(sys, "stdout", io.TextIOWrapper(io.BytesIO(), encoding="utf-8"))
    assert main(["words", str(path), "--password-stdin"]) == code


@pytest.mark.parametrize(
    ("line", "code"),
    [("u\r\n", 0), ("u\n", 0), ("u", 0), ("u \n", 2)],
    ids=["crlf", "lf", "no-newline", "trailing-space-kept"],
)
def test_password_stdin_strips_only_line_ending(
    line: str, code: int, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = write_pdf(tmp_path, pdf_factory.encrypted(user_pw="u"))
    monkeypatch.setattr(sys, "stdin", io.StringIO(line))
    monkeypatch.setattr(sys, "stdout", io.TextIOWrapper(io.BytesIO(), encoding="utf-8"))
    assert main(["words", str(path), "--password-stdin"]) == code


def test_L7_version(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--version"]) == 0
    assert capsys.readouterr().out.strip() == f"inkgrid {importlib.metadata.version('inkgrid')}"


@pytest.mark.parametrize("argv", [[], ["frobnicate"]], ids=["none", "unknown"])
def test_L8_bad_usage_exits_2(argv: list[str], capsys: pytest.CaptureFixture[str]) -> None:
    assert main(argv) == 2
    assert "usage: inkgrid" in capsys.readouterr().err


def test_L9_python_dash_m(tmp_path: Path) -> None:
    path = write_pdf(tmp_path, pdf_factory.simple_text())
    done = subprocess.run(
        [sys.executable, "-m", "inkgrid", "words", str(path)],
        capture_output=True,
        check=False,
        timeout=120,
    )
    assert done.returncode == 0, done.stderr
    assert Reading.model_validate_json(done.stdout).source.pages == 1


def test_console_script_is_registered() -> None:
    (script,) = importlib.metadata.entry_points(group="console_scripts", name="inkgrid")
    assert script.value == "inkgrid.cli:main"


def test_cli_writes_utf8_on_cp1252_console(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = write_pdf(tmp_path, pdf_factory.euro_text())
    console = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")
    monkeypatch.setattr(sys, "stdout", console)
    assert main(["words", str(path)]) == 0
    raw = console.buffer.getvalue()
    reading = Reading.model_validate_json(raw)
    assert [w.text for w in reading.words()] == pdf_factory.EURO_TEXT.split()
    assert "\u0141".encode() in raw


def test_L10_unwritable_output_exits_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = write_pdf(tmp_path, pdf_factory.simple_text())
    target = tmp_path / "missing" / "out.json"
    assert main(["words", str(path), "-o", str(target)]) == 2
    err = capsys.readouterr().err
    assert err.startswith("inkgrid: cannot write")
    assert err.count("\n") == 1


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX pipe semantics")
def test_L11_closed_pipe_ends_quietly(tmp_path: Path) -> None:
    import pymupdf

    doc = pymupdf.open()
    for _ in range(4):
        page = doc.new_page()
        for row in range(60):
            page.insert_text(
                (20, 20 + row * 12), " ".join(f"w{row}x{i}" for i in range(14)), fontsize=8
            )
    path = write_pdf(tmp_path, doc.tobytes())
    with subprocess.Popen(
        [sys.executable, "-m", "inkgrid", "words", str(path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ) as proc:
        assert proc.stdout is not None
        assert proc.stderr is not None
        proc.stdout.read(1)
        proc.stdout.close()
        err = proc.stderr.read()
        code = proc.wait(timeout=120)
    assert code == 0
    assert err == b""


def test_L12_password_is_read_as_utf8_whatever_the_locale(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    secret = "p\u00e4ssw\u00f6rd"
    path = write_pdf(tmp_path, pdf_factory.encrypted(user_pw=secret))
    stdin = io.TextIOWrapper(io.BytesIO(secret.encode("utf-8") + b"\n"), encoding="latin-1")
    monkeypatch.setattr(sys, "stdin", stdin)
    monkeypatch.setattr(sys, "stdout", io.TextIOWrapper(io.BytesIO(), encoding="utf-8"))
    assert main(["words", str(path), "--password-stdin"]) == 0


def test_L13_password_that_is_not_utf8_exits_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    path = write_pdf(tmp_path, pdf_factory.encrypted(user_pw="secret"))
    stdin = io.TextIOWrapper(io.BytesIO(b"p\xe4ss\n"), encoding="latin-1")
    monkeypatch.setattr(sys, "stdin", stdin)
    assert main(["words", str(path), "--password-stdin"]) == 2
    err = capsys.readouterr().err
    assert err.count("\n") == 1
    assert "not UTF-8" in err


@pytest.mark.parametrize("make", pdf_factory.OPENABLE.values(), ids=pdf_factory.OPENABLE.keys())
def test_CR1_read_prints_a_valid_document_for_every_fixture(
    make: Callable[[], bytes], tmp_path: Path, capsysbinary: pytest.CaptureFixture[bytes]
) -> None:
    path = write_pdf(tmp_path, make())
    assert main(["read", str(path)]) == 0
    out, err = capsysbinary.readouterr()
    assert err == b""
    assert Document.model_validate_json(out).source.file_name == "in.pdf"


def test_CR2_markdown_inspector_and_json_files(
    tmp_path: Path, capsysbinary: pytest.CaptureFixture[bytes]
) -> None:
    path = write_pdf(tmp_path, pdf_factory.two_column())
    md, html, out = tmp_path / "out.md", tmp_path / "out.html", tmp_path / "out.json"
    argv = ["read", str(path), "--markdown", str(md), "--inspector", str(html), "-o", str(out)]
    assert main(argv) == 0
    assert capsysbinary.readouterr() == (b"", b"")
    doc = Document.model_validate_json(out.read_bytes())
    assert md.read_text(encoding="utf-8") == doc.to_markdown()
    assert html.read_text(encoding="utf-8").startswith("<!doctype html>")


def test_CR3_strict_exits_1_and_still_writes_the_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = write_pdf(tmp_path, pdf_factory.image_only())
    out = tmp_path / "out.json"
    assert main(["read", str(path), "--strict", "-o", str(out)]) == 1
    assert Document.model_validate_json(out.read_bytes()).complete is False
    err = capsys.readouterr().err
    assert "no_text_layer" in err
    assert "Traceback" not in err


def test_CR4_a_missing_file_exits_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["read", str(tmp_path / "absent.pdf")]) == 2
    assert capsys.readouterr().err.startswith("inkgrid: ")


def test_CR5_an_unwritable_markdown_path_exits_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = write_pdf(tmp_path, pdf_factory.simple_text())
    target = tmp_path / "missing" / "out.md"
    assert main(["read", str(path), "--markdown", str(target), "-o", str(tmp_path / "o.json")]) == 2
    err = capsys.readouterr().err
    assert err.count("\n") == 1
    assert str(target) in err
