"""Tests for the MYP interpreter (tree-walking evaluator)."""

import math
import pytest

from myp.lexer import Lexer
from myp.parser import Parser
from myp.interpreter import Interpreter, RuntimeError as MYPRuntimeError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run(source: str) -> list[str]:
    """Run *source* and return all printed lines."""
    output_lines: list[str] = []
    tokens  = Lexer(source).tokenize()
    ast     = Parser(tokens).parse()
    Interpreter(output=output_lines.append).run(ast)
    return output_lines


def run_single(source: str) -> str:
    """Run *source* and return the first printed line."""
    return run(source)[0]


# ---------------------------------------------------------------------------
# Variable declarations & assignment
# ---------------------------------------------------------------------------

class TestVariables:
    def test_var_decl_and_print(self):
        assert run_single("VAR x = 7\nPRINT x\n") == "7"

    def test_const_decl_and_print(self):
        assert run_single("CONST C = 3.14\nPRINT C\n") == "3.14"

    def test_var_reassignment(self):
        src = "VAR x = 1\nx = 99\nPRINT x\n"
        assert run_single(src) == "99"

    def test_const_reassignment_raises(self):
        src = "CONST C = 1\nC = 2\n"
        with pytest.raises(MYPRuntimeError):
            run(src)

    def test_undefined_variable_raises(self):
        with pytest.raises(MYPRuntimeError):
            run("PRINT undefined_var\n")

    def test_undeclared_assign_raises(self):
        with pytest.raises(MYPRuntimeError):
            run("x = 5\n")  # x not declared with VAR


# ---------------------------------------------------------------------------
# Arithmetic
# ---------------------------------------------------------------------------

class TestArithmetic:
    def test_addition(self):
        assert run_single("PRINT 2 + 3\n") == "5"

    def test_subtraction(self):
        assert run_single("PRINT 10 - 4\n") == "6"

    def test_multiplication(self):
        assert run_single("PRINT 3 * 4\n") == "12"

    def test_division(self):
        assert run_single("PRINT 10 / 4\n") == "2.5"

    def test_power_caret(self):
        assert run_single("PRINT 2 ^ 10\n") == "1024"

    def test_power_starstar(self):
        assert run_single("PRINT 2 ** 8\n") == "256"

    def test_unary_minus(self):
        assert run_single("PRINT -5\n") == "-5"

    def test_division_by_zero(self):
        with pytest.raises(MYPRuntimeError):
            run("PRINT 1 / 0\n")

    def test_precedence_mul_over_add(self):
        assert run_single("PRINT 2 + 3 * 4\n") == "14"

    def test_parentheses(self):
        assert run_single("PRINT (2 + 3) * 4\n") == "20"


# ---------------------------------------------------------------------------
# Comparison and logical operators
# ---------------------------------------------------------------------------

class TestLogic:
    @pytest.mark.parametrize("src,expected", [
        ("PRINT 1 == 1\n",   "true"),
        ("PRINT 1 != 2\n",   "true"),
        ("PRINT 3 < 5\n",    "true"),
        ("PRINT 5 > 3\n",    "true"),
        ("PRINT 3 <= 3\n",   "true"),
        ("PRINT 4 >= 5\n",   "false"),
        ("PRINT 1 == 2\n",   "false"),
    ])
    def test_comparison(self, src, expected):
        assert run_single(src) == expected

    def test_and_true(self):
        assert run_single("PRINT 1 == 1 AND 2 == 2\n") == "true"

    def test_and_false(self):
        assert run_single("PRINT 1 == 1 AND 1 == 2\n") == "false"

    def test_or_true(self):
        assert run_single("PRINT 1 == 2 OR 2 == 2\n") == "true"

    def test_not(self):
        assert run_single("PRINT NOT 1 == 1\n") == "false"


# ---------------------------------------------------------------------------
# PRINT statement
# ---------------------------------------------------------------------------

class TestPrint:
    def test_print_string(self):
        assert run_single('PRINT "hello"\n') == "hello"

    def test_print_multiple_args(self):
        line = run_single('PRINT "x =", 5\n')
        assert "x =" in line
        assert "5" in line

    def test_print_empty(self):
        lines = run("PRINT\n")
        assert lines == [""]

    def test_print_string_concat(self):
        line = run_single('PRINT "a" + "b"\n')
        assert line == "ab"


# ---------------------------------------------------------------------------
# For loop
# ---------------------------------------------------------------------------

class TestForLoop:
    def test_basic_loop(self):
        src = "FOR i FROM 1 TO 3\n    PRINT i\nEND FOR\n"
        lines = run(src)
        assert lines == ["1", "2", "3"]

    def test_loop_step(self):
        src = "FOR i FROM 0 TO 6 STEP 2\n    PRINT i\nEND FOR\n"
        lines = run(src)
        assert lines == ["0", "2", "4", "6"]

    def test_loop_zero_iterations(self):
        src = "FOR i FROM 5 TO 3\n    PRINT i\nEND FOR\n"
        assert run(src) == []

    def test_loop_variable_scoped(self):
        # After loop, 'i' should not be accessible (it is in a child scope)
        src = "FOR i FROM 1 TO 1\n    PRINT i\nEND FOR\nPRINT i\n"
        with pytest.raises(MYPRuntimeError):
            run(src)


# ---------------------------------------------------------------------------
# If statement
# ---------------------------------------------------------------------------

class TestIfStmt:
    def test_if_true(self):
        src = "VAR x = 5\nIF x > 3 THEN\n    PRINT \"yes\"\nEND IF\n"
        assert run(src) == ["yes"]

    def test_if_false(self):
        src = "VAR x = 1\nIF x > 3 THEN\n    PRINT \"yes\"\nEND IF\n"
        assert run(src) == []

    def test_if_else_true_branch(self):
        src = (
            "VAR x = 5\n"
            "IF x > 3 THEN\n"
            "    PRINT \"big\"\n"
            "ELSE\n"
            "    PRINT \"small\"\n"
            "END IF\n"
        )
        assert run(src) == ["big"]

    def test_if_else_false_branch(self):
        src = (
            "VAR x = 1\n"
            "IF x > 3 THEN\n"
            "    PRINT \"big\"\n"
            "ELSE\n"
            "    PRINT \"small\"\n"
            "END IF\n"
        )
        assert run(src) == ["small"]


# ---------------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------------

class TestFunctions:
    def test_simple_function(self):
        src = (
            "FUNCTION double(x)\n"
            "    RETURN x * 2\n"
            "END FUNCTION\n"
            "PRINT double(7)\n"
        )
        assert run_single(src) == "14"

    def test_function_two_params(self):
        src = (
            "FUNCTION add(a, b)\n"
            "    RETURN a + b\n"
            "END FUNCTION\n"
            "PRINT add(3, 4)\n"
        )
        assert run_single(src) == "7"

    def test_function_wrong_arity_raises(self):
        src = (
            "FUNCTION f(x)\n"
            "    RETURN x\n"
            "END FUNCTION\n"
            "PRINT f(1, 2)\n"
        )
        with pytest.raises(MYPRuntimeError):
            run(src)

    def test_recursive_function(self):
        src = (
            "FUNCTION fact(n)\n"
            "    IF n <= 1 THEN\n"
            "        RETURN 1\n"
            "    END IF\n"
            "    RETURN n * fact(n - 1)\n"
            "END FUNCTION\n"
            "PRINT fact(5)\n"
        )
        assert run_single(src) == "120"

    def test_closure_captures_global(self):
        src = (
            "CONST SCALE = 10\n"
            "FUNCTION scale_it(x)\n"
            "    RETURN x * SCALE\n"
            "END FUNCTION\n"
            "PRINT scale_it(3)\n"
        )
        assert run_single(src) == "30"


# ---------------------------------------------------------------------------
# Built-in math functions
# ---------------------------------------------------------------------------

class TestBuiltinMath:
    @pytest.mark.parametrize("src,expected", [
        ("PRINT exp(0)\n",         "1"),
        ("PRINT sqrt(4)\n",        "2"),
        ("PRINT abs(-7)\n",        "7"),
        ("PRINT floor(2.9)\n",     "2"),
        ("PRINT ceil(2.1)\n",      "3"),
        ("PRINT round(2.5)\n",     "2"),   # Python banker's rounding
        ("PRINT min(3, 5)\n",      "3"),
        ("PRINT max(3, 5)\n",      "5"),
    ])
    def test_math_builtin(self, src, expected):
        assert run_single(src) == expected

    def test_ln(self):
        result = float(run_single("PRINT ln(2.718281828)\n"))
        assert result == pytest.approx(1.0, rel=1e-5)

    def test_log10(self):
        assert run_single("PRINT log10(1000)\n") == "3"

    def test_sin_pi_over_2(self):
        result = float(run_single("PRINT sin(pi())\n"))
        assert result == pytest.approx(0.0, abs=1e-10)

    def test_pi(self):
        result = float(run_single("PRINT pi()\n"))
        assert result == pytest.approx(math.pi)


# ---------------------------------------------------------------------------
# Built-in physics functions
# ---------------------------------------------------------------------------

class TestBuiltinPhysics:
    def test_number_density(self):
        # N_H in water: rho=1 g/cm³, A=18.015, n_per_mol=2
        result = float(run_single(
            "PRINT number_density(1.0, 18.015, 2.0)\n"
        ))
        expected = (1.0 * 6.02214076e23 * 2.0) / 18.015
        assert result == pytest.approx(expected, rel=1e-6)

    def test_macro_xsec(self):
        # Σ = N * σ_barn * 1e-24
        result = float(run_single(
            "PRINT macro_xsec(6.686e22, 0.3326)\n"
        ))
        expected = 6.686e22 * 0.3326 * 1e-24
        assert result == pytest.approx(expected, rel=1e-4)

    def test_diffusion_coeff(self):
        result = float(run_single("PRINT diffusion_coeff(3.0)\n"))
        # Printed with 6 significant figures; tolerate rounding at 6th sig fig
        assert result == pytest.approx(1.0 / 9.0, rel=1e-5)

    def test_diffusion_coeff_zero_raises(self):
        with pytest.raises(MYPRuntimeError):
            run("PRINT diffusion_coeff(0.0)\n")

    def test_attenuated_flux(self):
        # phi(z) = phi0 * exp(-Sigma_t * z)
        result = float(run_single("PRINT attenuated_flux(1.0e9, 2.69, 3.0)\n"))
        expected = 1.0e9 * math.exp(-2.69 * 3.0)
        assert result == pytest.approx(expected, rel=1e-6)

    def test_dose_rate_gy_s(self):
        # D' = phi * Sigma * Q_MeV * 1.60218e-13 / (rho * 1e-3)
        phi, Sigma, Q, rho = 1.0e9, 0.007, 2.31, 1.0
        result = float(run_single(
            f"PRINT dose_rate_gy_s({phi}, {Sigma}, {Q}, {rho})\n"
        ))
        J_per_MeV = 1.60218e-13
        rho_kg = rho * 1e-3
        expected = phi * Sigma * Q * J_per_MeV / rho_kg
        # Printed with 6 significant figures; tolerate rounding at 6th sig fig
        assert result == pytest.approx(expected, rel=1e-5)


# ---------------------------------------------------------------------------
# Pre-loaded global constants
# ---------------------------------------------------------------------------

class TestGlobalConstants:
    def test_avogadro(self):
        result = float(run_single("PRINT AVOGADRO\n"))
        # Printed with 6 significant figures; tolerate rounding at 6th sig fig
        assert result == pytest.approx(6.02214076e23, rel=1e-5)

    def test_mev_to_joule(self):
        result = float(run_single("PRINT MEV_TO_JOULE\n"))
        assert result == pytest.approx(1.60218e-13, rel=1e-6)


# ---------------------------------------------------------------------------
# End-to-end: the water_phantom sample
# ---------------------------------------------------------------------------

class TestWaterPhantomSample:
    """Run the full sample program and verify key output values."""

    @pytest.fixture(scope="class")
    @classmethod
    def output(cls):
        import os
        sample_path = os.path.join(
            os.path.dirname(__file__), "..", "examples", "water_phantom.myp"
        )
        with open(sample_path, encoding="utf-8") as fh:
            source = fh.read()
        return run(source)

    def test_runs_without_error(self, output):
        assert len(output) > 0

    def test_contains_completion_line(self, output):
        assert any("Calculation complete" in line for line in output)

    def test_flux_at_surface_is_phi0(self, output):
        # First flux table line: z=0 → phi = 1e9
        flux_lines = [l for l in output if "1000000000" in l and "|" in l]
        assert len(flux_lines) >= 1

    def test_summary_section_present(self, output):
        assert any("Summary" in line for line in output)
