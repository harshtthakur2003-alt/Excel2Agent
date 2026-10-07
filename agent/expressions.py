"""A small, safe expression evaluator used for decision rules and calculations.

Decision logic from the Excel file (e.g. ``current_stock < minimum_stock`` or
``abs(pct_diff) > 10``) is written as plain expressions in the YAML bindings.
Only arithmetic, comparisons, boolean logic and a whitelist of functions are
allowed - no attribute access, imports or arbitrary calls.
"""
from __future__ import annotations

import ast
import math
import operator
import re
from typing import Any


def _num(x: Any) -> Any:
    if isinstance(x, str):
        s = x.strip().replace(",", "").replace("$", "")
        if s == "":
            return None
        try:
            return float(s) if "." in s else int(s)
        except ValueError:
            return x
    return x


def _coalesce(*vals):
    for v in vals:
        if v is not None and v != "":
            return v
    return None


def _ceil_to(value, multiple):
    value, multiple = _num(value), _num(multiple) or 1
    if value is None:
        return None
    return int(math.ceil(value / multiple) * multiple)


def _pct_diff(a, b):
    a, b = _num(a), _num(b)
    if a is None or b in (None, 0):
        return None
    return round((a - b) / b * 100, 2)


def _norm(s):
    return re.sub(r"\s+", " ", str(s or "")).strip().upper()


def _norm_text(s):
    s = str(s or "").lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _none_safe(fn):
    def wrapper(*args):
        if any(a is None for a in args):
            return None
        return fn(*args)
    return wrapper


FUNCTIONS = {
    "abs": _none_safe(abs), "min": _none_safe(min), "max": _none_safe(max), "round": _none_safe(round), "len": len,
    "int": int, "float": float, "str": str, "bool": bool,
    "ceil": _none_safe(math.ceil), "floor": _none_safe(math.floor),
    "num": _num, "coalesce": _coalesce, "ceil_to": _ceil_to, "pct_diff": _pct_diff,
    "norm": _norm, "norm_text": _norm_text,
    "lower": lambda s: str(s or "").lower(), "upper": lambda s: str(s or "").upper(),
    "strip": lambda s: str(s or "").strip(),
    "is_blank": lambda v: v is None or str(v).strip() == "",
}

_BIN = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod,
        ast.Pow: operator.pow}
_CMP = {ast.Lt: operator.lt, ast.LtE: operator.le, ast.Gt: operator.gt, ast.GtE: operator.ge,
        ast.Eq: operator.eq, ast.NotEq: operator.ne,
        ast.In: lambda a, b: a in b, ast.NotIn: lambda a, b: a not in b}


class ExpressionError(ValueError):
    pass


def evaluate(expr: str, variables: dict) -> Any:
    try:
        tree = ast.parse(str(expr), mode="eval")
    except SyntaxError as exc:
        raise ExpressionError(f"Invalid expression '{expr}': {exc}") from exc
    return _eval(tree.body, variables, expr)


def _eval(node, env, src):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        if node.id in env:
            return _num(env[node.id])
        if node.id in ("True", "False", "None"):
            return {"True": True, "False": False, "None": None}[node.id]
        raise ExpressionError(f"Unknown variable '{node.id}' in '{src}'")
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN:
        left, right = _eval(node.left, env, src), _eval(node.right, env, src)
        if left is None or right is None:
            return None
        return _BIN[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp):
        val = _eval(node.operand, env, src)
        if isinstance(node.op, ast.Not):
            return not val
        if isinstance(node.op, ast.USub):
            return None if val is None else -val
        if isinstance(node.op, ast.UAdd):
            return val
    if isinstance(node, ast.BoolOp):
        vals = [_eval(v, env, src) for v in node.values]
        return all(vals) if isinstance(node.op, ast.And) else any(vals)
    if isinstance(node, ast.Compare):
        left = _eval(node.left, env, src)
        for op, comp in zip(node.ops, node.comparators):
            right = _eval(comp, env, src)
            if type(op) not in _CMP:
                raise ExpressionError(f"Operator not allowed in '{src}'")
            if left is None or right is None:
                if type(op) in (ast.Eq, ast.NotEq):
                    if not _CMP[type(op)](left, right):
                        return False
                    left = right
                    continue
                return False          # comparisons with missing values are False
            if not _CMP[type(op)](left, right):
                return False
            left = right
        return True
    if isinstance(node, ast.IfExp):
        return _eval(node.body, env, src) if _eval(node.test, env, src) else _eval(node.orelse, env, src)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in FUNCTIONS:
        args = [_eval(a, env, src) for a in node.args]
        return FUNCTIONS[node.func.id](*args)
    if isinstance(node, (ast.List, ast.Tuple)):
        return [_eval(e, env, src) for e in node.elts]
    raise ExpressionError(f"Unsupported syntax in expression '{src}'")
