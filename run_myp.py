#!/usr/bin/env python3
"""
run_myp.py — Command-line entry point for the MYP interpreter.

Usage
-----
    python run_myp.py <program.myp>

Example
-------
    python run_myp.py examples/water_phantom.myp
"""

import sys
import os

# Ensure the package root is on the path when run directly
sys.path.insert(0, os.path.dirname(__file__))

from myp import Lexer, Parser, Interpreter
from myp.lexer import LexerError
from myp.parser import ParseError
from myp.interpreter import RuntimeError as MYPRuntimeError


def run_file(path: str) -> int:
    """
    Read, lex, parse and interpret a MYP source file.

    Returns
    -------
    int
        Exit code: 0 on success, 1 on error.
    """
    try:
        with open(path, "r", encoding="utf-8") as fh:
            source = fh.read()
    except OSError as exc:
        print(f"Error: cannot read '{path}': {exc}", file=sys.stderr)
        return 1

    try:
        tokens  = Lexer(source).tokenize()
        ast     = Parser(tokens).parse()
        Interpreter().run(ast)
    except LexerError as exc:
        print(f"Lexer error: {exc}", file=sys.stderr)
        return 1
    except ParseError as exc:
        print(f"Parse error: {exc}", file=sys.stderr)
        return 1
    except MYPRuntimeError as exc:
        print(f"Runtime error: {exc}", file=sys.stderr)
        return 1

    return 0


def main() -> None:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <program.myp>", file=sys.stderr)
        sys.exit(1)
    sys.exit(run_file(sys.argv[1]))


if __name__ == "__main__":
    main()
