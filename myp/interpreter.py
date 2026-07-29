"""
MYP Interpreter — tree-walking evaluator for the MYP AST.

Built-in functions
------------------
Math  : exp, sqrt, ln, log10, abs, sin, cos, tan, floor, ceil, round,
        min, max, pi
Physics (BNCT helpers):
        macro_xsec(N, sigma_barn) -> macroscopic cross-section (cm⁻¹)
        number_density(rho, A, n_per_mol) -> atom number density (cm⁻³)
        diffusion_coeff(Sigma_tr) -> diffusion coefficient (cm)
        attenuated_flux(phi0, Sigma_t, z) -> exponential attenuation
        dose_rate_gy_s(phi, Sigma, Q_MeV, rho) -> absorbed dose rate (Gy/s)
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Callable

from .parser import (
    ProgramNode, ConstDeclNode, VarDeclNode, AssignNode, PrintNode,
    ForNode, IfNode, FuncDefNode, ReturnNode, ExprStmtNode,
    NumberNode, StringNode, IdentNode, BinOpNode, UnaryOpNode, CallNode,
    StmtNode, ExprNode,
)


# ---------------------------------------------------------------------------
# Error & control-flow signals
# ---------------------------------------------------------------------------

class RuntimeError(Exception):
    """Raised on a run-time error in a MYP program."""


class _ReturnSignal(Exception):
    """Internal: carries a RETURN value up the call stack."""
    def __init__(self, value: Any) -> None:
        self.value = value


# ---------------------------------------------------------------------------
# Environment (variable scopes)
# ---------------------------------------------------------------------------

class Environment:
    """A single scope frame with an optional parent."""

    def __init__(self, parent: Optional["Environment"] = None) -> None:
        self._vars: Dict[str, Any] = {}
        self._consts: Dict[str, Any] = {}
        self._parent = parent

    def define_var(self, name: str, value: Any) -> None:
        self._vars[name] = value

    def define_const(self, name: str, value: Any) -> None:
        if name in self._consts:
            raise RuntimeError(f"Constant '{name}' already defined")
        self._consts[name] = value

    def get(self, name: str) -> Any:
        if name in self._vars:
            return self._vars[name]
        if name in self._consts:
            return self._consts[name]
        if self._parent:
            return self._parent.get(name)
        raise RuntimeError(f"Undefined variable '{name}'")

    def assign(self, name: str, value: Any) -> None:
        if name in self._consts or (self._parent and self._parent._is_const(name)):
            raise RuntimeError(f"Cannot reassign constant '{name}'")
        if name in self._vars:
            self._vars[name] = value
            return
        if self._parent:
            try:
                self._parent.assign(name, value)
                return
            except RuntimeError:
                pass
        raise RuntimeError(f"Undefined variable '{name}' (use VAR to declare first)")

    def _is_const(self, name: str) -> bool:
        if name in self._consts:
            return True
        return bool(self._parent and self._parent._is_const(name))


# ---------------------------------------------------------------------------
# Built-in functions
# ---------------------------------------------------------------------------

def _builtin_macro_xsec(N: float, sigma_barn: float) -> float:
    """
    Macroscopic cross-section: Σ = N · σ   [cm⁻¹]

    Parameters
    ----------
    N          : atom number density (atoms/cm³)
    sigma_barn : microscopic cross-section (barn = 1e-24 cm²)
    """
    return N * sigma_barn * 1e-24


def _builtin_number_density(rho: float, A: float, n_per_mol: float) -> float:
    """
    Atom number density: N = (ρ · Nₐ · n_per_mol) / A   [atoms/cm³]

    Parameters
    ----------
    rho       : material density (g/cm³)
    A         : molar mass of the compound (g/mol)
    n_per_mol : atoms of the element per formula unit
    """
    NA = 6.02214076e23   # Avogadro constant (mol⁻¹)
    return (rho * NA * n_per_mol) / A


def _builtin_diffusion_coeff(Sigma_tr: float) -> float:
    """
    Diffusion coefficient: D = 1 / (3 Σ_tr)   [cm]

    Parameters
    ----------
    Sigma_tr : macroscopic transport cross-section (cm⁻¹)
    """
    if Sigma_tr <= 0:
        raise RuntimeError("diffusion_coeff: Sigma_tr must be positive")
    return 1.0 / (3.0 * Sigma_tr)


def _builtin_attenuated_flux(phi0: float, Sigma_t: float, z: float) -> float:
    """
    Exponential attenuation of the uncollided beam flux:
    Φ(z) = Φ₀ · exp(−Σ_t · z)

    Parameters
    ----------
    phi0    : incident flux at the surface (n/cm²/s)
    Sigma_t : total macroscopic cross-section (cm⁻¹)
    z       : depth into the phantom (cm)
    """
    return phi0 * math.exp(-Sigma_t * z)


def _builtin_dose_rate_gy_s(phi: float, Sigma: float, Q_MeV: float, rho: float) -> float:
    """
    Absorbed dose rate from a neutron reaction (Gy/s):
    D' = Φ · Σ · Q / ρ

    Parameters
    ----------
    phi   : neutron flux (n/cm²/s)
    Sigma : macroscopic cross-section for the reaction (cm⁻¹)
    Q_MeV : energy deposited per reaction (MeV)
    rho   : material density (g/cm³)
    """
    J_per_MeV = 1.60218e-13   # joules per MeV
    g_per_kg   = 1e-3
    # D' [Gy/s] = Φ [n/cm²/s] · Σ [cm⁻¹] · Q [J] / (ρ [g/cm³] · 1e3 [g/kg])
    # = Φ · Σ · Q_J / (ρ_kg_per_cm3)
    rho_kg_cm3 = rho * g_per_kg
    return phi * Sigma * (Q_MeV * J_per_MeV) / rho_kg_cm3


BUILTINS: Dict[str, Callable] = {
    # Standard math
    "exp":    lambda x: math.exp(x),
    "sqrt":   lambda x: math.sqrt(x),
    "ln":     lambda x: math.log(x),
    "log10":  lambda x: math.log10(x),
    "abs":    lambda x: abs(x),
    "sin":    lambda x: math.sin(x),
    "cos":    lambda x: math.cos(x),
    "tan":    lambda x: math.tan(x),
    "floor":  lambda x: float(math.floor(x)),
    "ceil":   lambda x: float(math.ceil(x)),
    "round":  lambda x: float(round(x)),
    "min":    lambda a, b: min(a, b),
    "max":    lambda a, b: max(a, b),
    "pi":     lambda: math.pi,
    # Physics helpers
    "macro_xsec":      _builtin_macro_xsec,
    "number_density":  _builtin_number_density,
    "diffusion_coeff": _builtin_diffusion_coeff,
    "attenuated_flux": _builtin_attenuated_flux,
    "dose_rate_gy_s":  _builtin_dose_rate_gy_s,
}


# ---------------------------------------------------------------------------
# User-defined function wrapper
# ---------------------------------------------------------------------------

class MYPFunction:
    def __init__(self, node: FuncDefNode, closure: Environment) -> None:
        self.node    = node
        self.closure = closure


# ---------------------------------------------------------------------------
# Interpreter
# ---------------------------------------------------------------------------

class Interpreter:
    """
    Tree-walking interpreter for MYP programs.

    Usage::

        from myp import Lexer, Parser, Interpreter
        tokens = Lexer(source).tokenize()
        ast    = Parser(tokens).parse()
        interp = Interpreter()
        interp.run(ast)
    """

    def __init__(self, output: Optional[Callable[[str], None]] = None) -> None:
        """
        Parameters
        ----------
        output:
            Callable that receives printed lines (default: ``print``).
        """
        self._output = output or print
        self._global  = Environment()
        self._load_builtins()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, program: ProgramNode) -> None:
        """Execute a parsed MYP :class:`ProgramNode`."""
        self._exec_stmts(program.statements, self._global)

    # ------------------------------------------------------------------
    # Statement execution
    # ------------------------------------------------------------------

    def _exec_stmts(self, stmts: List[StmtNode], env: Environment) -> None:
        for stmt in stmts:
            self._exec(stmt, env)

    def _exec(self, stmt: StmtNode, env: Environment) -> None:  # noqa: C901
        if isinstance(stmt, ConstDeclNode):
            val = self._eval(stmt.value, env)
            env.define_const(stmt.name, val)

        elif isinstance(stmt, VarDeclNode):
            val = self._eval(stmt.value, env)
            env.define_var(stmt.name, val)

        elif isinstance(stmt, AssignNode):
            val = self._eval(stmt.value, env)
            env.assign(stmt.name, val)

        elif isinstance(stmt, PrintNode):
            parts = []
            for arg in stmt.args:
                v = self._eval(arg, env)
                parts.append(self._to_str(v))
            self._output(" ".join(parts) if parts else "")

        elif isinstance(stmt, ForNode):
            self._exec_for(stmt, env)

        elif isinstance(stmt, IfNode):
            self._exec_if(stmt, env)

        elif isinstance(stmt, FuncDefNode):
            fn = MYPFunction(stmt, env)
            env.define_var(stmt.name, fn)

        elif isinstance(stmt, ReturnNode):
            val = self._eval(stmt.value, env)
            raise _ReturnSignal(val)

        elif isinstance(stmt, ExprStmtNode):
            self._eval(stmt.expr, env)

        else:
            raise RuntimeError(f"Unknown statement type: {type(stmt).__name__}")

    def _exec_for(self, node: ForNode, env: Environment) -> None:
        start = self._eval(node.start, env)
        end   = self._eval(node.end, env)
        step  = self._eval(node.step, env) if node.step else 1.0

        if not isinstance(start, (int, float)):
            raise RuntimeError("FOR loop start must be a number")
        if not isinstance(end, (int, float)):
            raise RuntimeError("FOR loop end must be a number")
        if not isinstance(step, (int, float)):
            raise RuntimeError("FOR loop step must be a number")
        if step == 0:
            raise RuntimeError("FOR loop step cannot be zero")

        loop_env = Environment(parent=env)
        current = float(start)
        while (step > 0 and current <= end + 1e-12 * abs(end)) or \
              (step < 0 and current >= end - 1e-12 * abs(end)):
            loop_env.define_var(node.var, current)
            self._exec_stmts(node.body, loop_env)
            current += step
            # Re-read the var in case body reassigned it, but update current
            # from the arithmetic step (loop variable is step-controlled)

    def _exec_if(self, node: IfNode, env: Environment) -> None:
        cond = self._eval(node.condition, env)
        if self._is_truthy(cond):
            branch_env = Environment(parent=env)
            self._exec_stmts(node.then_body, branch_env)
        elif node.else_body is not None:
            branch_env = Environment(parent=env)
            self._exec_stmts(node.else_body, branch_env)

    # ------------------------------------------------------------------
    # Expression evaluation
    # ------------------------------------------------------------------

    def _eval(self, expr: ExprNode, env: Environment) -> Any:  # noqa: C901
        if isinstance(expr, NumberNode):
            return expr.value

        if isinstance(expr, StringNode):
            return expr.value

        if isinstance(expr, IdentNode):
            return env.get(expr.name)

        if isinstance(expr, UnaryOpNode):
            val = self._eval(expr.operand, env)
            if expr.op == "-":
                return -val
            if expr.op == "NOT":
                return not self._is_truthy(val)
            raise RuntimeError(f"Unknown unary operator: {expr.op}")

        if isinstance(expr, BinOpNode):
            return self._eval_binop(expr, env)

        if isinstance(expr, CallNode):
            return self._eval_call(expr, env)

        raise RuntimeError(f"Unknown expression type: {type(expr).__name__}")

    def _eval_binop(self, expr: BinOpNode, env: Environment) -> Any:  # noqa: C901
        op = expr.op
        # Short-circuit logical operators
        if op == "AND":
            left = self._eval(expr.left, env)
            return left if not self._is_truthy(left) else self._eval(expr.right, env)
        if op == "OR":
            left = self._eval(expr.left, env)
            return left if self._is_truthy(left) else self._eval(expr.right, env)

        left  = self._eval(expr.left, env)
        right = self._eval(expr.right, env)

        if op == "+":
            if isinstance(left, str) or isinstance(right, str):
                return self._to_str(left) + self._to_str(right)
            return left + right
        if op == "-":  return left - right
        if op == "*":  return left * right
        if op == "/":
            if right == 0:
                raise RuntimeError("Division by zero")
            return left / right
        if op == "**": return left ** right
        if op == "==": return left == right
        if op == "!=": return left != right
        if op == "<":  return left < right
        if op == ">":  return left > right
        if op == "<=": return left <= right
        if op == ">=": return left >= right

        raise RuntimeError(f"Unknown binary operator: {op!r}")

    def _eval_call(self, expr: CallNode, env: Environment) -> Any:
        # Look up as a user function first, then builtins
        fn: Any = None
        try:
            fn = env.get(expr.name)
        except RuntimeError:
            pass

        args = [self._eval(a, env) for a in expr.args]

        if isinstance(fn, MYPFunction):
            return self._call_user_func(fn, args, expr.line)

        if fn is None and expr.name in BUILTINS:
            try:
                return BUILTINS[expr.name](*args)
            except Exception as e:
                raise RuntimeError(f"Line {expr.line}: built-in '{expr.name}' error: {e}") from e

        if callable(fn):
            return fn(*args)

        raise RuntimeError(f"Line {expr.line}: '{expr.name}' is not a function")

    def _call_user_func(self, fn: MYPFunction, args: List[Any], line: int) -> Any:
        node = fn.node
        if len(args) != len(node.params):
            raise RuntimeError(
                f"Line {line}: '{node.name}' expects {len(node.params)} argument(s), "
                f"got {len(args)}"
            )
        call_env = Environment(parent=fn.closure)
        for param, val in zip(node.params, args):
            call_env.define_var(param, val)
        try:
            self._exec_stmts(node.body, call_env)
        except _ReturnSignal as ret:
            return ret.value
        return None

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def _is_truthy(self, val: Any) -> bool:
        if isinstance(val, bool):
            return val
        if isinstance(val, (int, float)):
            return val != 0
        if isinstance(val, str):
            return bool(val)
        return val is not None

    @staticmethod
    def _to_str(val: Any) -> str:
        if isinstance(val, bool):
            return "true" if val else "false"
        if isinstance(val, float):
            # Use a compact but readable representation
            if val == int(val) and abs(val) < 1e15:
                return str(int(val))
            return f"{val:.6g}"
        return str(val)

    def _load_builtins(self) -> None:
        """Pre-load built-in constants into the global environment."""
        self._global.define_const("AVOGADRO",      6.02214076e23)
        self._global.define_const("NEUTRON_MASS",  1.67492749804e-24)   # g
        self._global.define_const("PLANCK",        6.62607015e-34)       # J·s
        self._global.define_const("SPEED_OF_LIGHT", 2.99792458e10)       # cm/s
        self._global.define_const("EV_TO_JOULE",   1.60218e-19)
        self._global.define_const("MEV_TO_JOULE",  1.60218e-13)
        self._global.define_const("BARN_TO_CM2",   1e-24)
