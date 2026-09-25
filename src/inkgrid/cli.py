"""The `inkgrid` command line. M0 provides `inkgrid words`, the raw page model as JSON.

Exit codes: 0 success; 1 reserved for defects and strict mode (later milestones); 2 usage errors
and unreadable input. Output is always UTF-8 bytes, whatever the console's encoding.
"""

import argparse
import importlib.metadata
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from inkgrid.api import read_pages
from inkgrid.errors import InkgridError

EXIT_OK = 0
EXIT_USAGE = 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="inkgrid",
        description="Exact tables and text from born-digital PDFs.",
    )
    parser.add_argument(
        "--version", action="version", version=f"inkgrid {importlib.metadata.version('inkgrid')}"
    )
    commands = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")
    words = commands.add_parser("words", help="print the raw page model (words, rules) as JSON")
    words.add_argument("pdf", type=Path, help="the PDF to read")
    words.add_argument("-o", "--output", type=Path, help="write the JSON here instead of stdout")
    words.add_argument("--pretty", action="store_true", help="indent the JSON for reading")
    words.add_argument(
        "--password-stdin",
        action="store_true",
        help="read the password from the first line of stdin (never from argv)",
    )
    return parser


def _password_from_stdin() -> str:
    """The first stdin line, read as UTF-8 bytes, with only its line ending removed.

    Raises:
        UnicodeDecodeError: the line is not UTF-8.
    """
    buffer = getattr(sys.stdin, "buffer", None)
    line: str = sys.stdin.readline() if buffer is None else buffer.readline().decode("utf-8")
    return line.removesuffix("\n").removesuffix("\r")


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


def _emit(data: bytes, output: Path | None) -> int:
    if output is not None:
        try:
            output.write_bytes(data)
        except OSError as exc:
            sys.stderr.write(f"inkgrid: cannot write {output}: {exc.strerror or exc}\n")
            return EXIT_USAGE
        return EXIT_OK
    try:
        _write_stdout(data)
    except BrokenPipeError:
        # The reader stopped early (`inkgrid words f.pdf | head`); what it read was correct.
        _discard_stdout()
    return EXIT_OK


def _words(args: argparse.Namespace) -> int:
    try:
        password = _password_from_stdin() if args.password_stdin else None
    except UnicodeDecodeError:
        sys.stderr.write("inkgrid: the password on stdin is not UTF-8\n")
        return EXIT_USAGE
    try:
        reading = read_pages(args.pdf, password=password)
    except InkgridError as exc:
        sys.stderr.write(f"inkgrid: {exc}\n")
        return EXIT_USAGE
    text = reading.model_dump_json(indent=2) if args.pretty else reading.model_dump_json()
    return _emit(text.encode("utf-8") + b"\n", args.output)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line and return its exit code."""
    try:
        args = _parser().parse_args(argv)
    except SystemExit as exc:
        code = exc.code
        return code if isinstance(code, int) else (EXIT_OK if code is None else EXIT_USAGE)
    return _words(args)
