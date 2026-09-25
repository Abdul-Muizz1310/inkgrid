"""The `inkgrid` command line. M0 provides `inkgrid words`, the raw page model as JSON.

Exit codes: 0 success; 1 reserved for defects and strict mode (later milestones); 2 usage errors
and unreadable input. Output is always UTF-8 bytes, whatever the console's encoding.
"""

import argparse
import importlib.metadata
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
    """The first stdin line with only its line ending removed."""
    line = sys.stdin.readline()
    line = line.removesuffix("\n")
    return line.removesuffix("\r")


def _emit(data: bytes, output: Path | None) -> None:
    if output is not None:
        output.write_bytes(data)
        return
    buffer = getattr(sys.stdout, "buffer", None)
    if buffer is None:
        sys.stdout.write(data.decode("utf-8"))
    else:
        sys.stdout.flush()
        buffer.write(data)
        buffer.flush()


def _words(args: argparse.Namespace) -> int:
    password = _password_from_stdin() if args.password_stdin else None
    try:
        reading = read_pages(args.pdf, password=password)
    except InkgridError as exc:
        sys.stderr.write(f"inkgrid: {exc}\n")
        return EXIT_USAGE
    text = reading.model_dump_json(indent=2) if args.pretty else reading.model_dump_json()
    _emit(text.encode("utf-8") + b"\n", args.output)
    return EXIT_OK


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line and return its exit code."""
    try:
        args = _parser().parse_args(argv)
    except SystemExit as exc:
        code = exc.code
        return code if isinstance(code, int) else (EXIT_OK if code is None else EXIT_USAGE)
    return _words(args)
