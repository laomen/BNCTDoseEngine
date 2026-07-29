"""
MYP Lexer — converts MYP source text into a flat list of tokens.

Token types
-----------
Literals   : NUMBER, STRING
Identifiers: IDENT
Keywords   : CONST, VAR, PRINT, FOR, FROM, TO, STEP, END,
             IF, THEN, ELSE, AND, OR, NOT,
             FUNCTION, RETURN
Operators  : PLUS, MINUS, STAR, SLASH, POWER,
             ASSIGN, EQ, NE, LT, GT, LE, GE
Punctuation: LPAREN, RPAREN, COMMA
Structure  : NEWLINE, EOF
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import List


# ---------------------------------------------------------------------------
# Token types
# ---------------------------------------------------------------------------

class TokenType(Enum):
    # Literals
    NUMBER  = auto()
    STRING  = auto()
    # Names
    IDENT   = auto()
    # Keywords
    CONST    = auto()
    VAR      = auto()
    PRINT    = auto()
    FOR      = auto()
    FROM     = auto()
    TO       = auto()
    STEP     = auto()
    END      = auto()
    IF       = auto()
    THEN     = auto()
    ELSE     = auto()
    AND      = auto()
    OR       = auto()
    NOT      = auto()
    FUNCTION = auto()
    RETURN   = auto()
    # Operators
    PLUS   = auto()
    MINUS  = auto()
    STAR   = auto()
    SLASH  = auto()
    POWER  = auto()
    ASSIGN = auto()
    EQ     = auto()
    NE     = auto()
    LT     = auto()
    GT     = auto()
    LE     = auto()
    GE     = auto()
    # Punctuation
    LPAREN = auto()
    RPAREN = auto()
    COMMA  = auto()
    # Structure
    NEWLINE = auto()
    EOF     = auto()


KEYWORDS: dict[str, TokenType] = {
    "CONST":    TokenType.CONST,
    "VAR":      TokenType.VAR,
    "PRINT":    TokenType.PRINT,
    "FOR":      TokenType.FOR,
    "FROM":     TokenType.FROM,
    "TO":       TokenType.TO,
    "STEP":     TokenType.STEP,
    "END":      TokenType.END,
    "IF":       TokenType.IF,
    "THEN":     TokenType.THEN,
    "ELSE":     TokenType.ELSE,
    "AND":      TokenType.AND,
    "OR":       TokenType.OR,
    "NOT":      TokenType.NOT,
    "FUNCTION": TokenType.FUNCTION,
    "RETURN":   TokenType.RETURN,
}


# ---------------------------------------------------------------------------
# Token dataclass
# ---------------------------------------------------------------------------

@dataclass
class Token:
    type:  TokenType
    value: object   # str | float | None
    line:  int
    col:   int

    def __repr__(self) -> str:
        return f"Token({self.type.name}, {self.value!r}, {self.line}:{self.col})"


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class LexerError(Exception):
    """Raised when the lexer encounters an unexpected character."""


# ---------------------------------------------------------------------------
# Lexer
# ---------------------------------------------------------------------------

class Lexer:
    """Converts a MYP source string into a list of :class:`Token` objects."""

    def __init__(self, source: str) -> None:
        self._src  = source
        self._pos  = 0
        self._line = 1
        self._col  = 1

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def tokenize(self) -> List[Token]:
        """Lex *source* and return all tokens (ending with EOF)."""
        tokens: List[Token] = []
        while self._pos < len(self._src):
            self._skip_whitespace()
            if self._pos >= len(self._src):
                break
            ch = self._peek()
            if ch == "\n":
                tokens.append(Token(TokenType.NEWLINE, "\n", self._line, self._col))
                self._advance()
            elif ch == "#":
                self._skip_line_comment()
            elif ch.isdigit() or (ch == "." and self._peek(1).isdigit()):
                tokens.append(self._read_number())
            elif ch == '"':
                tokens.append(self._read_string())
            elif ch.isalpha() or ch == "_":
                tokens.append(self._read_ident())
            else:
                tokens.append(self._read_operator())
        tokens.append(Token(TokenType.EOF, None, self._line, self._col))
        return tokens

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _peek(self, offset: int = 0) -> str:
        pos = self._pos + offset
        return self._src[pos] if pos < len(self._src) else "\0"

    def _advance(self) -> str:
        ch = self._src[self._pos]
        self._pos += 1
        if ch == "\n":
            self._line += 1
            self._col = 1
        else:
            self._col += 1
        return ch

    def _skip_whitespace(self) -> None:
        while self._pos < len(self._src) and self._src[self._pos] in " \t\r":
            self._advance()

    def _skip_line_comment(self) -> None:
        while self._pos < len(self._src) and self._src[self._pos] != "\n":
            self._advance()

    def _read_number(self) -> Token:
        line, col = self._line, self._col
        s = ""
        while self._pos < len(self._src) and (self._src[self._pos].isdigit() or self._src[self._pos] == "."):
            s += self._advance()
        if self._pos < len(self._src) and self._src[self._pos] in "eE":
            s += self._advance()
            if self._pos < len(self._src) and self._src[self._pos] in "+-":
                s += self._advance()
            while self._pos < len(self._src) and self._src[self._pos].isdigit():
                s += self._advance()
        return Token(TokenType.NUMBER, float(s), line, col)

    def _read_string(self) -> Token:
        line, col = self._line, self._col
        self._advance()  # opening "
        s = ""
        while self._pos < len(self._src) and self._src[self._pos] != '"':
            ch = self._advance()
            if ch == "\\" and self._pos < len(self._src):
                esc = self._advance()
                ch = {"n": "\n", "t": "\t", "\\": "\\", '"': '"'}.get(esc, esc)
            s += ch
        if self._pos >= len(self._src):
            raise LexerError(f"Unterminated string literal at line {line}")
        self._advance()  # closing "
        return Token(TokenType.STRING, s, line, col)

    def _read_ident(self) -> Token:
        line, col = self._line, self._col
        s = ""
        while self._pos < len(self._src) and (self._src[self._pos].isalnum() or self._src[self._pos] == "_"):
            s += self._advance()
        ttype = KEYWORDS.get(s, TokenType.IDENT)
        return Token(ttype, s, line, col)

    def _read_operator(self) -> Token:
        line, col = self._line, self._col
        ch = self._advance()
        nxt = self._peek()

        two_char: dict[str, TokenType] = {
            "**": TokenType.POWER,
            "==": TokenType.EQ,
            "!=": TokenType.NE,
            "<=": TokenType.LE,
            ">=": TokenType.GE,
        }
        if ch + nxt in two_char:
            self._advance()
            return Token(two_char[ch + nxt], ch + nxt, line, col)

        one_char: dict[str, TokenType] = {
            "+": TokenType.PLUS,
            "-": TokenType.MINUS,
            "*": TokenType.STAR,
            "/": TokenType.SLASH,
            "^": TokenType.POWER,
            "=": TokenType.ASSIGN,
            "<": TokenType.LT,
            ">": TokenType.GT,
            "(": TokenType.LPAREN,
            ")": TokenType.RPAREN,
            ",": TokenType.COMMA,
        }
        if ch in one_char:
            return Token(one_char[ch], ch, line, col)

        raise LexerError(f"Unexpected character {ch!r} at line {line}, col {col}")
