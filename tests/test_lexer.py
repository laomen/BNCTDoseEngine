"""Tests for the MYP lexer."""

import pytest
from myp.lexer import Lexer, Token, TokenType, LexerError


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def lex(source: str):
    """Lex *source* and return all non-EOF tokens."""
    return [t for t in Lexer(source).tokenize() if t.type != TokenType.EOF]


def types(source: str):
    """Return just the token types (excluding NEWLINE and EOF)."""
    return [
        t.type for t in Lexer(source).tokenize()
        if t.type not in (TokenType.EOF, TokenType.NEWLINE)
    ]


# ---------------------------------------------------------------------------
# Numbers
# ---------------------------------------------------------------------------

class TestNumbers:
    def test_integer(self):
        toks = lex("42")
        assert toks[0].type  == TokenType.NUMBER
        assert toks[0].value == 42.0

    def test_float(self):
        toks = lex("3.14")
        assert toks[0].value == pytest.approx(3.14)

    def test_scientific_positive(self):
        toks = lex("1.5e3")
        assert toks[0].value == pytest.approx(1500.0)

    def test_scientific_negative(self):
        toks = lex("2.0e-4")
        assert toks[0].value == pytest.approx(2.0e-4)

    def test_scientific_uppercase(self):
        toks = lex("1E10")
        assert toks[0].value == pytest.approx(1e10)


# ---------------------------------------------------------------------------
# Strings
# ---------------------------------------------------------------------------

class TestStrings:
    def test_basic(self):
        toks = lex('"hello"')
        assert toks[0].type  == TokenType.STRING
        assert toks[0].value == "hello"

    def test_escape_newline(self):
        toks = lex(r'"a\nb"')
        assert toks[0].value == "a\nb"

    def test_escape_tab(self):
        toks = lex(r'"a\tb"')
        assert toks[0].value == "a\tb"

    def test_unterminated_raises(self):
        with pytest.raises(LexerError):
            Lexer('"unterminated').tokenize()


# ---------------------------------------------------------------------------
# Keywords
# ---------------------------------------------------------------------------

class TestKeywords:
    @pytest.mark.parametrize("kw,expected", [
        ("CONST",    TokenType.CONST),
        ("VAR",      TokenType.VAR),
        ("PRINT",    TokenType.PRINT),
        ("FOR",      TokenType.FOR),
        ("FROM",     TokenType.FROM),
        ("TO",       TokenType.TO),
        ("STEP",     TokenType.STEP),
        ("END",      TokenType.END),
        ("IF",       TokenType.IF),
        ("THEN",     TokenType.THEN),
        ("ELSE",     TokenType.ELSE),
        ("AND",      TokenType.AND),
        ("OR",       TokenType.OR),
        ("NOT",      TokenType.NOT),
        ("FUNCTION", TokenType.FUNCTION),
        ("RETURN",   TokenType.RETURN),
    ])
    def test_keyword(self, kw, expected):
        assert types(kw) == [expected]

    def test_ident_not_keyword(self):
        assert types("myvar") == [TokenType.IDENT]

    def test_ident_value(self):
        toks = lex("myvar")
        assert toks[0].value == "myvar"


# ---------------------------------------------------------------------------
# Operators and punctuation
# ---------------------------------------------------------------------------

class TestOperators:
    @pytest.mark.parametrize("src,expected", [
        ("+",  TokenType.PLUS),
        ("-",  TokenType.MINUS),
        ("*",  TokenType.STAR),
        ("/",  TokenType.SLASH),
        ("^",  TokenType.POWER),
        ("**", TokenType.POWER),
        ("=",  TokenType.ASSIGN),
        ("==", TokenType.EQ),
        ("!=", TokenType.NE),
        ("<",  TokenType.LT),
        (">",  TokenType.GT),
        ("<=", TokenType.LE),
        (">=", TokenType.GE),
        ("(",  TokenType.LPAREN),
        (")",  TokenType.RPAREN),
        (",",  TokenType.COMMA),
    ])
    def test_operator(self, src, expected):
        assert types(src) == [expected]


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------

class TestComments:
    def test_comment_ignored(self):
        assert types("# this is a comment") == []

    def test_comment_after_code(self):
        tks = types("42 # comment")
        assert tks == [TokenType.NUMBER]

    def test_multiline_comment(self):
        src = "VAR x = 1  # first\nVAR y = 2  # second\n"
        tks = types(src)
        assert tks == [
            TokenType.VAR, TokenType.IDENT, TokenType.ASSIGN, TokenType.NUMBER,
            TokenType.VAR, TokenType.IDENT, TokenType.ASSIGN, TokenType.NUMBER,
        ]


# ---------------------------------------------------------------------------
# Newlines
# ---------------------------------------------------------------------------

class TestNewlines:
    def test_newline_token_present(self):
        toks = Lexer("x\ny").tokenize()
        types_list = [t.type for t in toks if t.type != TokenType.EOF]
        assert TokenType.NEWLINE in types_list

    def test_no_newline_for_blank_source(self):
        toks = Lexer("").tokenize()
        assert len(toks) == 1
        assert toks[0].type == TokenType.EOF


# ---------------------------------------------------------------------------
# Line / column tracking
# ---------------------------------------------------------------------------

class TestPositions:
    def test_first_token_line1(self):
        toks = lex("VAR")
        assert toks[0].line == 1

    def test_second_line(self):
        src = "VAR x = 1\nVAR y = 2\n"
        toks = Lexer(src).tokenize()
        var_y = next(t for t in toks if t.type == TokenType.VAR and t.line == 2)
        assert var_y.line == 2


# ---------------------------------------------------------------------------
# Unexpected character
# ---------------------------------------------------------------------------

class TestLexerErrors:
    def test_unexpected_char(self):
        with pytest.raises(LexerError):
            Lexer("@bad").tokenize()
