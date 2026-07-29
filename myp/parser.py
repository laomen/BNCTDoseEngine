"""
MYP Parser — converts a token stream into an Abstract Syntax Tree (AST).

Grammar (simplified BNF)
------------------------
program     ::= statement* EOF
statement   ::= const_decl
              | var_decl
              | assign_stmt
              | print_stmt
              | for_stmt
              | if_stmt
              | func_def
              | return_stmt
              | expr_stmt          # bare expression (e.g. function call)

const_decl  ::= CONST IDENT ASSIGN expr NEWLINE
var_decl    ::= VAR IDENT ASSIGN expr NEWLINE
assign_stmt ::= IDENT ASSIGN expr NEWLINE
print_stmt  ::= PRINT print_arg (COMMA print_arg)* NEWLINE
print_arg   ::= STRING | expr
for_stmt    ::= FOR IDENT FROM expr TO expr (STEP expr)? NEWLINE
                    statement*
                END FOR NEWLINE
if_stmt     ::= IF expr THEN NEWLINE
                    statement*
               (ELSE NEWLINE
                    statement*)?
                END IF NEWLINE
func_def    ::= FUNCTION IDENT LPAREN param_list RPAREN NEWLINE
                    statement*
                END FUNCTION NEWLINE
param_list  ::= (IDENT (COMMA IDENT)*)?
return_stmt ::= RETURN expr NEWLINE
expr_stmt   ::= expr NEWLINE

expr        ::= or_expr
or_expr     ::= and_expr (OR and_expr)*
and_expr    ::= not_expr (AND not_expr)*
not_expr    ::= NOT not_expr | comparison
comparison  ::= addition ((EQ|NE|LT|GT|LE|GE) addition)*
addition    ::= term ((PLUS|MINUS) term)*
term        ::= factor ((STAR|SLASH) factor)*
factor      ::= (PLUS|MINUS) factor | power
power       ::= primary (POWER factor)*
primary     ::= NUMBER | STRING | LPAREN expr RPAREN | IDENT | call_expr
call_expr   ::= IDENT LPAREN arg_list RPAREN
arg_list    ::= (expr (COMMA expr)*)?
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Union

from .lexer import Token, TokenType


# ---------------------------------------------------------------------------
# AST node definitions
# ---------------------------------------------------------------------------

@dataclass
class NumberNode:
    value: float
    line: int = 0


@dataclass
class StringNode:
    value: str
    line: int = 0


@dataclass
class IdentNode:
    name: str
    line: int = 0


@dataclass
class BinOpNode:
    op: str
    left: "ExprNode"
    right: "ExprNode"
    line: int = 0


@dataclass
class UnaryOpNode:
    op: str
    operand: "ExprNode"
    line: int = 0


@dataclass
class CallNode:
    name: str
    args: List["ExprNode"]
    line: int = 0


# Statement nodes

@dataclass
class ConstDeclNode:
    name: str
    value: "ExprNode"
    line: int = 0


@dataclass
class VarDeclNode:
    name: str
    value: "ExprNode"
    line: int = 0


@dataclass
class AssignNode:
    name: str
    value: "ExprNode"
    line: int = 0


@dataclass
class PrintNode:
    args: List[Union["ExprNode", StringNode]]
    line: int = 0


@dataclass
class ForNode:
    var: str
    start: "ExprNode"
    end: "ExprNode"
    step: Optional["ExprNode"]
    body: List["StmtNode"]
    line: int = 0


@dataclass
class IfNode:
    condition: "ExprNode"
    then_body: List["StmtNode"]
    else_body: Optional[List["StmtNode"]]
    line: int = 0


@dataclass
class FuncDefNode:
    name: str
    params: List[str]
    body: List["StmtNode"]
    line: int = 0


@dataclass
class ReturnNode:
    value: "ExprNode"
    line: int = 0


@dataclass
class ExprStmtNode:
    expr: "ExprNode"
    line: int = 0


@dataclass
class ProgramNode:
    statements: List["StmtNode"] = field(default_factory=list)


ExprNode = Union[
    NumberNode, StringNode, IdentNode, BinOpNode, UnaryOpNode, CallNode
]

StmtNode = Union[
    ConstDeclNode, VarDeclNode, AssignNode, PrintNode,
    ForNode, IfNode, FuncDefNode, ReturnNode, ExprStmtNode,
]


# ---------------------------------------------------------------------------
# Error
# ---------------------------------------------------------------------------

class ParseError(Exception):
    """Raised on a syntax error in the MYP source."""


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class Parser:
    """
    Recursive-descent parser.

    Parameters
    ----------
    tokens:
        The flat token list produced by :class:`~myp.lexer.Lexer`.
    """

    def __init__(self, tokens: List[Token]) -> None:
        # Filter out NEWLINE tokens that appear inside expressions; we keep
        # them only at the statement level.  We re-insert them as sentinels.
        self._tokens = tokens
        self._pos = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse(self) -> ProgramNode:
        """Parse all tokens and return the root :class:`ProgramNode`."""
        self._skip_newlines()
        stmts: List[StmtNode] = []
        while not self._check(TokenType.EOF):
            stmts.append(self._statement())
            self._skip_newlines()
        return ProgramNode(stmts)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _peek(self, offset: int = 0) -> Token:
        pos = self._pos + offset
        if pos < len(self._tokens):
            return self._tokens[pos]
        return self._tokens[-1]  # EOF

    def _advance(self) -> Token:
        tok = self._tokens[self._pos]
        if tok.type != TokenType.EOF:
            self._pos += 1
        return tok

    def _check(self, *types: TokenType) -> bool:
        return self._peek().type in types

    def _match(self, *types: TokenType) -> bool:
        if self._check(*types):
            self._advance()
            return True
        return False

    def _expect(self, ttype: TokenType, msg: str = "") -> Token:
        tok = self._peek()
        if tok.type != ttype:
            hint = msg or f"expected {ttype.name}"
            raise ParseError(
                f"Line {tok.line}: {hint}, got {tok.type.name}({tok.value!r})"
            )
        return self._advance()

    def _skip_newlines(self) -> None:
        while self._check(TokenType.NEWLINE):
            self._advance()

    def _expect_newline_or_eof(self) -> None:
        if self._check(TokenType.EOF):
            return
        self._expect(TokenType.NEWLINE, "expected newline after statement")
        self._skip_newlines()

    # ------------------------------------------------------------------
    # Statement parsers
    # ------------------------------------------------------------------

    def _statement(self) -> StmtNode:
        tok = self._peek()

        if tok.type == TokenType.CONST:
            return self._const_decl()
        if tok.type == TokenType.VAR:
            return self._var_decl()
        if tok.type == TokenType.PRINT:
            return self._print_stmt()
        if tok.type == TokenType.FOR:
            return self._for_stmt()
        if tok.type == TokenType.IF:
            return self._if_stmt()
        if tok.type == TokenType.FUNCTION:
            return self._func_def()
        if tok.type == TokenType.RETURN:
            return self._return_stmt()
        if tok.type == TokenType.IDENT and self._peek(1).type == TokenType.ASSIGN:
            return self._assign_stmt()

        # Bare expression statement (e.g. a function call)
        expr = self._expr()
        self._expect_newline_or_eof()
        return ExprStmtNode(expr=expr, line=tok.line)

    def _const_decl(self) -> ConstDeclNode:
        tok = self._expect(TokenType.CONST)
        name = self._expect(TokenType.IDENT, "expected identifier after CONST").value
        self._expect(TokenType.ASSIGN, "expected '=' after constant name")
        val = self._expr()
        self._expect_newline_or_eof()
        return ConstDeclNode(name=name, value=val, line=tok.line)

    def _var_decl(self) -> VarDeclNode:
        tok = self._expect(TokenType.VAR)
        name = self._expect(TokenType.IDENT, "expected identifier after VAR").value
        self._expect(TokenType.ASSIGN, "expected '=' after variable name")
        val = self._expr()
        self._expect_newline_or_eof()
        return VarDeclNode(name=name, value=val, line=tok.line)

    def _assign_stmt(self) -> AssignNode:
        tok = self._expect(TokenType.IDENT)
        self._expect(TokenType.ASSIGN)
        val = self._expr()
        self._expect_newline_or_eof()
        return AssignNode(name=tok.value, value=val, line=tok.line)

    def _print_stmt(self) -> PrintNode:
        tok = self._expect(TokenType.PRINT)
        args: List[ExprNode] = []
        # PRINT with no arguments is allowed (prints a blank line)
        if not self._check(TokenType.NEWLINE, TokenType.EOF):
            args.append(self._expr())
            while self._match(TokenType.COMMA):
                args.append(self._expr())
        self._expect_newline_or_eof()
        return PrintNode(args=args, line=tok.line)

    def _for_stmt(self) -> ForNode:
        tok = self._expect(TokenType.FOR)
        var = self._expect(TokenType.IDENT, "expected loop variable after FOR").value
        self._expect(TokenType.FROM, "expected FROM")
        start = self._expr()
        self._expect(TokenType.TO, "expected TO")
        end = self._expr()
        step: Optional[ExprNode] = None
        if self._match(TokenType.STEP):
            step = self._expr()
        self._expect_newline_or_eof()
        body = self._body_until_end("FOR")
        return ForNode(var=var, start=start, end=end, step=step, body=body, line=tok.line)

    def _if_stmt(self) -> IfNode:
        tok = self._expect(TokenType.IF)
        cond = self._expr()
        self._expect(TokenType.THEN, "expected THEN after IF condition")
        self._expect_newline_or_eof()

        then_body: List[StmtNode] = []
        else_body: Optional[List[StmtNode]] = None

        while not self._check(TokenType.END, TokenType.ELSE, TokenType.EOF):
            then_body.append(self._statement())
            self._skip_newlines()

        if self._check(TokenType.ELSE):
            self._advance()  # consume ELSE
            self._expect_newline_or_eof()
            else_body = []
            while not self._check(TokenType.END, TokenType.EOF):
                else_body.append(self._statement())
                self._skip_newlines()

        self._expect(TokenType.END, "expected END IF")
        self._expect(TokenType.IF, "expected IF after END")
        self._expect_newline_or_eof()
        return IfNode(condition=cond, then_body=then_body, else_body=else_body, line=tok.line)

    def _func_def(self) -> FuncDefNode:
        tok = self._expect(TokenType.FUNCTION)
        name = self._expect(TokenType.IDENT, "expected function name").value
        self._expect(TokenType.LPAREN)
        params: List[str] = []
        if not self._check(TokenType.RPAREN):
            params.append(self._expect(TokenType.IDENT, "expected parameter name").value)
            while self._match(TokenType.COMMA):
                params.append(self._expect(TokenType.IDENT, "expected parameter name").value)
        self._expect(TokenType.RPAREN)
        self._expect_newline_or_eof()
        body = self._body_until_end("FUNCTION")
        return FuncDefNode(name=name, params=params, body=body, line=tok.line)

    def _return_stmt(self) -> ReturnNode:
        tok = self._expect(TokenType.RETURN)
        val = self._expr()
        self._expect_newline_or_eof()
        return ReturnNode(value=val, line=tok.line)

    def _body_until_end(self, keyword: str) -> List[StmtNode]:
        """Parse statements until END <keyword>."""
        body: List[StmtNode] = []
        self._skip_newlines()
        end_kw = getattr(TokenType, keyword)
        while not (self._check(TokenType.END) and self._peek(1).type == end_kw):
            if self._check(TokenType.EOF):
                raise ParseError(f"Unexpected EOF; expected END {keyword}")
            body.append(self._statement())
            self._skip_newlines()
        self._expect(TokenType.END)
        self._expect(end_kw, f"expected {keyword} after END")
        self._expect_newline_or_eof()
        return body

    # ------------------------------------------------------------------
    # Expression parsers (operator precedence via recursive descent)
    # ------------------------------------------------------------------

    def _expr(self) -> ExprNode:
        return self._or_expr()

    def _or_expr(self) -> ExprNode:
        left = self._and_expr()
        while self._check(TokenType.OR):
            op_tok = self._advance()
            right = self._and_expr()
            left = BinOpNode(op="OR", left=left, right=right, line=op_tok.line)
        return left

    def _and_expr(self) -> ExprNode:
        left = self._not_expr()
        while self._check(TokenType.AND):
            op_tok = self._advance()
            right = self._not_expr()
            left = BinOpNode(op="AND", left=left, right=right, line=op_tok.line)
        return left

    def _not_expr(self) -> ExprNode:
        if self._check(TokenType.NOT):
            op_tok = self._advance()
            operand = self._not_expr()
            return UnaryOpNode(op="NOT", operand=operand, line=op_tok.line)
        return self._comparison()

    _CMP_OPS = {
        TokenType.EQ: "==",
        TokenType.NE: "!=",
        TokenType.LT: "<",
        TokenType.GT: ">",
        TokenType.LE: "<=",
        TokenType.GE: ">=",
    }

    def _comparison(self) -> ExprNode:
        left = self._addition()
        while self._peek().type in self._CMP_OPS:
            op_tok = self._advance()
            right = self._addition()
            left = BinOpNode(op=self._CMP_OPS[op_tok.type], left=left, right=right, line=op_tok.line)
        return left

    def _addition(self) -> ExprNode:
        left = self._term()
        while self._check(TokenType.PLUS, TokenType.MINUS):
            op_tok = self._advance()
            right = self._term()
            left = BinOpNode(op=op_tok.value, left=left, right=right, line=op_tok.line)
        return left

    def _term(self) -> ExprNode:
        left = self._factor()
        while self._check(TokenType.STAR, TokenType.SLASH):
            op_tok = self._advance()
            right = self._factor()
            left = BinOpNode(op=op_tok.value, left=left, right=right, line=op_tok.line)
        return left

    def _factor(self) -> ExprNode:
        if self._check(TokenType.MINUS):
            op_tok = self._advance()
            operand = self._factor()
            return UnaryOpNode(op="-", operand=operand, line=op_tok.line)
        if self._check(TokenType.PLUS):
            self._advance()
            return self._factor()
        return self._power()

    def _power(self) -> ExprNode:
        base = self._primary()
        if self._check(TokenType.POWER):
            op_tok = self._advance()
            exp = self._factor()   # right-associative
            return BinOpNode(op="**", left=base, right=exp, line=op_tok.line)
        return base

    def _primary(self) -> ExprNode:
        tok = self._peek()

        if tok.type == TokenType.NUMBER:
            self._advance()
            return NumberNode(value=tok.value, line=tok.line)

        if tok.type == TokenType.STRING:
            self._advance()
            return StringNode(value=tok.value, line=tok.line)

        if tok.type == TokenType.LPAREN:
            self._advance()
            expr = self._expr()
            self._expect(TokenType.RPAREN, "expected ')'")
            return expr

        if tok.type == TokenType.IDENT:
            # Peek ahead for function call
            if self._peek(1).type == TokenType.LPAREN:
                return self._call_expr()
            self._advance()
            return IdentNode(name=tok.value, line=tok.line)

        raise ParseError(
            f"Line {tok.line}: unexpected token {tok.type.name}({tok.value!r}) in expression"
        )

    def _call_expr(self) -> CallNode:
        name_tok = self._expect(TokenType.IDENT)
        self._expect(TokenType.LPAREN)
        args: List[ExprNode] = []
        if not self._check(TokenType.RPAREN):
            args.append(self._expr())
            while self._match(TokenType.COMMA):
                args.append(self._expr())
        self._expect(TokenType.RPAREN, "expected ')' after argument list")
        return CallNode(name=name_tok.value, args=args, line=name_tok.line)
