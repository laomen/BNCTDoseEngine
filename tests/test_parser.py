"""Tests for the MYP parser."""

import pytest
from myp.lexer import Lexer
from myp.parser import (
    Parser, ParseError,
    ProgramNode, ConstDeclNode, VarDeclNode, AssignNode,
    PrintNode, ForNode, IfNode, FuncDefNode, ReturnNode, ExprStmtNode,
    NumberNode, StringNode, IdentNode, BinOpNode, UnaryOpNode, CallNode,
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def parse(source: str) -> ProgramNode:
    tokens = Lexer(source).tokenize()
    return Parser(tokens).parse()


def first_stmt(source: str):
    return parse(source).statements[0]


# ---------------------------------------------------------------------------
# Declarations
# ---------------------------------------------------------------------------

class TestDeclarations:
    def test_const_decl(self):
        node = first_stmt("CONST PI = 3.14\n")
        assert isinstance(node, ConstDeclNode)
        assert node.name == "PI"
        assert isinstance(node.value, NumberNode)
        assert node.value.value == pytest.approx(3.14)

    def test_var_decl(self):
        node = first_stmt("VAR x = 42\n")
        assert isinstance(node, VarDeclNode)
        assert node.name == "x"

    def test_assign(self):
        node = first_stmt("x = 10\n")
        assert isinstance(node, AssignNode)
        assert node.name == "x"

    def test_var_with_expr(self):
        node = first_stmt("VAR y = 2 + 3\n")
        assert isinstance(node.value, BinOpNode)
        assert node.value.op == "+"


# ---------------------------------------------------------------------------
# Print statement
# ---------------------------------------------------------------------------

class TestPrint:
    def test_print_string(self):
        node = first_stmt('PRINT "hello"\n')
        assert isinstance(node, PrintNode)
        assert len(node.args) == 1
        assert isinstance(node.args[0], StringNode)
        assert node.args[0].value == "hello"

    def test_print_multiple(self):
        node = first_stmt('PRINT "x =", x\n')
        assert len(node.args) == 2

    def test_print_no_args(self):
        node = first_stmt("PRINT\n")
        assert isinstance(node, PrintNode)
        assert node.args == []


# ---------------------------------------------------------------------------
# For loop
# ---------------------------------------------------------------------------

class TestForLoop:
    def test_basic_for(self):
        src = "FOR i FROM 0 TO 10\n    PRINT i\nEND FOR\n"
        node = first_stmt(src)
        assert isinstance(node, ForNode)
        assert node.var == "i"
        assert isinstance(node.start, NumberNode)
        assert node.start.value == 0.0
        assert isinstance(node.end,   NumberNode)
        assert node.end.value   == 10.0
        assert node.step is None
        assert len(node.body) == 1

    def test_for_with_step(self):
        src = "FOR i FROM 0 TO 10 STEP 2\n    PRINT i\nEND FOR\n"
        node = first_stmt(src)
        assert isinstance(node.step, NumberNode)
        assert node.step.value == 2.0


# ---------------------------------------------------------------------------
# If statement
# ---------------------------------------------------------------------------

class TestIfStmt:
    def test_basic_if(self):
        src = "IF x > 0 THEN\n    PRINT x\nEND IF\n"
        node = first_stmt(src)
        assert isinstance(node, IfNode)
        assert isinstance(node.condition, BinOpNode)
        assert node.condition.op == ">"
        assert node.else_body is None

    def test_if_else(self):
        src = (
            "IF x > 0 THEN\n"
            "    PRINT x\n"
            "ELSE\n"
            "    PRINT 0\n"
            "END IF\n"
        )
        node = first_stmt(src)
        assert isinstance(node, IfNode)
        assert node.else_body is not None
        assert len(node.else_body) == 1


# ---------------------------------------------------------------------------
# Function definition
# ---------------------------------------------------------------------------

class TestFuncDef:
    def test_basic_function(self):
        src = (
            "FUNCTION add(a, b)\n"
            "    RETURN a + b\n"
            "END FUNCTION\n"
        )
        node = first_stmt(src)
        assert isinstance(node, FuncDefNode)
        assert node.name   == "add"
        assert node.params == ["a", "b"]
        assert len(node.body) == 1
        assert isinstance(node.body[0], ReturnNode)

    def test_no_params(self):
        src = "FUNCTION greet()\n    PRINT \"hi\"\nEND FUNCTION\n"
        node = first_stmt(src)
        assert node.params == []


# ---------------------------------------------------------------------------
# Expressions
# ---------------------------------------------------------------------------

class TestExpressions:
    def test_number(self):
        node = first_stmt("x = 5\n")
        assert isinstance(node.value, NumberNode)

    def test_ident(self):
        node = first_stmt("y = x\n")
        assert isinstance(node.value, IdentNode)
        assert node.value.name == "x"

    def test_unary_minus(self):
        node = first_stmt("z = -3\n")
        assert isinstance(node.value, UnaryOpNode)
        assert node.value.op == "-"

    def test_binop_precedence(self):
        # 2 + 3 * 4 should parse as 2 + (3 * 4)
        node = first_stmt("r = 2 + 3 * 4\n")
        root = node.value
        assert isinstance(root, BinOpNode)
        assert root.op == "+"
        assert isinstance(root.right, BinOpNode)
        assert root.right.op == "*"

    def test_power_right_assoc(self):
        # 2 ** 3 ** 2 → 2 ** (3 ** 2)
        node = first_stmt("r = 2 ** 3 ** 2\n")
        root = node.value
        assert root.op == "**"
        assert isinstance(root.right, BinOpNode)
        assert root.right.op == "**"

    def test_parentheses(self):
        # (2 + 3) * 4
        node = first_stmt("r = (2 + 3) * 4\n")
        root = node.value
        assert root.op == "*"
        assert isinstance(root.left, BinOpNode)
        assert root.left.op == "+"

    def test_function_call_in_expr(self):
        node = first_stmt("r = exp(1.0)\n")
        assert isinstance(node.value, CallNode)
        assert node.value.name == "exp"
        assert len(node.value.args) == 1

    def test_comparison_ops(self):
        for op in ("==", "!=", "<", ">", "<=", ">="):
            node = first_stmt(f"r = a {op} b\n")
            assert node.value.op == op


# ---------------------------------------------------------------------------
# Parse errors
# ---------------------------------------------------------------------------

class TestParseErrors:
    def test_missing_assign_in_var(self):
        with pytest.raises(ParseError):
            parse("VAR x 5\n")

    def test_missing_end_for(self):
        with pytest.raises(ParseError):
            parse("FOR i FROM 0 TO 5\n    PRINT i\n")

    def test_missing_end_if(self):
        with pytest.raises(ParseError):
            parse("IF x > 0 THEN\n    PRINT x\n")
