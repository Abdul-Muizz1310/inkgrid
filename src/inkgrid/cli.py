"""The `inkgrid` command line: `read`, `verify`, and `words`.

`read` prints the `Document`, `verify` its report against the PDF, and `words` the page model. Exit
codes: 0 success; 1 strict mode found an error-severity finding, or verification found a
defect; 2 usage errors and unreadable input. Output is always UTF-8 bytes, whatever the console's
encoding.
"""

import argparse
import importlib.metadata
import os
import sys
from collections import Counter
from collections.abc import Callable, Sequence
from pathlib import Path

from inkgrid.api import read, read_pages, verify
from inkgrid.errors import PasswordRequired, PdfOpenError, SourceMismatch, WrongPassword
from inkgrid.model.document import Document, document_from_json
from inkgrid.model.findings import Severity, summarize
from inkgrid.model.page import Reading
from inkgrid.model.verification import DefectCode, VerificationReport
from inkgrid.render.inspector import build_inspector

EXIT_OK = 0
EXIT_STRICT = 1
EXIT_DEFECTS = 1
EXIT_USAGE = 2
INPUT_ERRORS = (PdfOpenError, PasswordRequired, WrongPassword)


class _UsageError(Exception):
    """A problem with the arguments or the input: one line on stderr, exit 2."""


def _add_common(command: argparse.ArgumentParser) -> None:
    command.add_argument("pdf", type=Path, help="the PDF to read")
    command.add_argument("-o", "--output", type=Path, help="write the JSON here instead of stdout")
    command.add_argument("--pretty", action="store_true", help="indent the JSON for reading")
    command.add_argument(
        "--password-stdin",
        action="store_true",
        help="read the password from the first line of stdin (never from argv)",
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="inkgrid",
        description="Exact tables and text from born-digital PDFs.",
    )
    parser.add_argument(
        "--version", action="version", version=f"inkgrid {importlib.metadata.version('inkgrid')}"
    )
    commands = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")
    read_command = commands.add_parser("read", help="print the Document (blocks, links) as JSON")
    _add_common(read_command)
    read_command.add_argument("--markdown", type=Path, help="also write the text as Markdown")
    read_command.add_argument("--inspector", type=Path, help="also write the HTML inspector")
    read_command.add_argument(
        "--strict", action="store_true", help="exit 1 when an error-severity finding is present"
    )
    read_command.add_argument(
        "--lattice",
        choices=("combined", "vector", "raster"),
        default="combined",
        help="Camelot's engine for ruled tables (default: combined)",
    )
    verify_command = commands.add_parser(
        "verify", help="grade a Document against its PDF; exit 1 on any defect"
    )
    _add_common(verify_command)
    verify_command.add_argument(
        "document", type=Path, help="the Document JSON `inkgrid read` wrote"
    )
    verify_command.add_argument(
        "--inspector", type=Path, help="also write the HTML inspector with the defects drawn"
    )
    words = commands.add_parser("words", help="print the raw page model (words, rules) as JSON")
    _add_common(words)
    return parser


def _password_from_stdin() -> str:
    """The first stdin line, read as UTF-8 bytes, with only its line ending removed.

    Raises:
        UnicodeDecodeError: the line is not UTF-8.
    """
    buffer = getattr(sys.stdin, "buffer", None)
    line: str = sys.stdin.readline() if buffer is None else buffer.readline().decode("utf-8")
    return line.removesuffix("\n").removesuffix("\r")


def _password(args: argparse.Namespace) -> str | None:
    if not args.password_stdin:
        return None
    try:
        return _password_from_stdin()
    except UnicodeDecodeError as exc:
        msg = "the password on stdin is not UTF-8"
        raise _UsageError(msg) from exc


def _write_stdout(data: bytes) -> None:
    buffer = getattr(sys.stdout, "buffer", None)
    if buffer is None:
        sys.stdout.write(data.decode("utf-8"))
        sys.stdout.flush()
    else:
        sys.stdout.flush()
        buffer.write(data)
        buffer.flush()


def _discard_stdout() -> None:
    """Point stdout at the null device, so the interpreter's final flush cannot fail again."""
    devnull = os.open(os.devnull, os.O_WRONLY)
    try:
        os.dup2(devnull, sys.stdout.fileno())
    finally:
        os.close(devnull)


def _write_file(path: Path, data: bytes) -> None:
    try:
        path.write_bytes(data)
    except OSError as exc:
        msg = f"cannot write {path}: {exc.strerror or exc}"
        raise _UsageError(msg) from exc


def _emit(model: Reading | Document | VerificationReport, args: argparse.Namespace) -> None:
    text = model.model_dump_json(indent=2) if args.pretty else model.model_dump_json()
    data = text.encode("utf-8") + b"\n"
    if args.output is not None:
        _write_file(args.output, data)
        return
    try:
        _write_stdout(data)
    except BrokenPipeError:
        # The reader stopped early (`inkgrid read f.pdf | head`); what it read was correct.
        _discard_stdout()


def _words(args: argparse.Namespace) -> int:
    _emit(read_pages(args.pdf, password=_password(args)), args)
    return EXIT_OK


def _read(args: argparse.Namespace) -> int:
    password = _password(args)
    doc = read(args.pdf, password=password, lattice=args.lattice)
    _emit(doc, args)
    if args.markdown is not None:
        _write_file(args.markdown, doc.to_markdown().encode("utf-8"))
    if args.inspector is not None:
        try:
            html = build_inspector(doc, args.pdf, password)
        except ValueError as exc:
            raise _UsageError(str(exc)) from exc
        _write_file(args.inspector, html.encode("utf-8"))
    if args.strict and not doc.complete:
        errors = [f for f in doc.findings if f.severity is Severity.ERROR]
        sys.stderr.write(f"inkgrid: strict mode: error findings: {summarize(errors)}\n")
        return EXIT_STRICT
    return EXIT_OK


def _load_document(path: Path) -> Document:
    try:
        text = path.read_bytes()
    except OSError as exc:
        msg = f"cannot read {path}: {exc.strerror or exc}"
        raise _UsageError(msg) from exc
    try:
        return document_from_json(text)
    except ValueError as exc:
        msg = f"{path} is not an inkgrid document: {exc}"
        raise _UsageError(msg) from exc


def _defect_summary(report: VerificationReport) -> str:
    counts = Counter(d.code for d in report.defects)
    total = len(report.defects)
    codes = ", ".join(f"{code.value} {counts[code]}" for code in DefectCode if counts[code])
    return f"{total} defect{'' if total == 1 else 's'}: {codes}"


def _verify(args: argparse.Namespace) -> int:
    password = _password(args)
    doc = _load_document(args.document)
    try:
        report = verify(doc, args.pdf, password=password)
    except SourceMismatch as exc:
        raise _UsageError(str(exc)) from exc
    _emit(report, args)
    if args.inspector is not None:
        html = build_inspector(doc, args.pdf, password, report)
        _write_file(args.inspector, html.encode("utf-8"))
    if not report.ok:
        sys.stderr.write(f"inkgrid: verify: {_defect_summary(report)}\n")
        return EXIT_DEFECTS
    return EXIT_OK


COMMANDS: dict[str, Callable[[argparse.Namespace], int]] = {
    "read": _read,
    "verify": _verify,
    "words": _words,
}


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line and return its exit code."""
    try:
        args = _parser().parse_args(argv)
    except SystemExit as exc:
        code = exc.code
        return code if isinstance(code, int) else (EXIT_OK if code is None else EXIT_USAGE)
    try:
        return COMMANDS[args.command](args)
    except (*INPUT_ERRORS, _UsageError) as exc:
        sys.stderr.write(f"inkgrid: {exc}\n")
        return EXIT_USAGE
