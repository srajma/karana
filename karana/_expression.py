from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence, Set, Union

ExpressionLike = Union["Expression", int, float]


def series(name: str) -> "SeriesRef":
    """
    Convenience helper to build expression trees for a region/series.
    """
    if not isinstance(name, str) or not name:
        raise ValueError("series() expects a non-empty region name string.")
    return SeriesRef(name=name)


def ensure_expression(value: ExpressionLike) -> "Expression":
    if isinstance(value, Expression):
        return value
    if isinstance(value, (int, float)):
        return Literal(float(value))
    raise TypeError(f"Unsupported operand type {type(value)!r} for expression composition.")


class Expression:
    """
    Symbolic arithmetic tree that can be compiled into placeholder expressions.
    """

    def __add__(self, other: ExpressionLike) -> "Expression":
        return BinaryOp("add", self, ensure_expression(other))

    def __radd__(self, other: ExpressionLike) -> "Expression":
        return ensure_expression(other).__add__(self)

    def __sub__(self, other: ExpressionLike) -> "Expression":
        return BinaryOp("sub", self, ensure_expression(other))

    def __rsub__(self, other: ExpressionLike) -> "Expression":
        return ensure_expression(other).__sub__(self)

    def __mul__(self, other: ExpressionLike) -> "Expression":
        return BinaryOp("mul", self, ensure_expression(other))

    def __rmul__(self, other: ExpressionLike) -> "Expression":
        return ensure_expression(other).__mul__(self)

    def __truediv__(self, other: ExpressionLike) -> "Expression":
        return BinaryOp("div", self, ensure_expression(other))

    def __rtruediv__(self, other: ExpressionLike) -> "Expression":
        return ensure_expression(other).__truediv__(self)

    def __neg__(self) -> "Expression":
        return UnaryOp("neg", self)

    # Collection helpers -----------------------------------------------------------------

    def collect_series(self) -> List[str]:
        """
        Return region names used in the expression in order of first appearance.
        """
        order: List[str] = []
        seen: Set[str] = set()
        self._collect_series(order, seen)
        return order

    def to_placeholder_expression(self, series_order: Sequence[str]) -> str:
        """
        Produce an infix expression string referencing entries in series_order (1-based).
        """
        mapping = {name: idx + 1 for idx, name in enumerate(series_order)}
        return self._to_placeholder(mapping, parent_prec=0)

    # Internal traversal -----------------------------------------------------------------

    def _collect_series(self, order: List[str], seen: Set[str]) -> None:
        raise NotImplementedError

    def _to_placeholder(self, mapping: dict[str, int], parent_prec: int) -> str:
        raise NotImplementedError


@dataclass(frozen=True)
class SeriesRef(Expression):
    name: str

    def _collect_series(self, order: List[str], seen: Set[str]) -> None:
        if self.name not in seen:
            seen.add(self.name)
            order.append(self.name)

    def _to_placeholder(self, mapping: dict[str, int], parent_prec: int) -> str:
        try:
            return str(mapping[self.name])
        except KeyError as exc:
            raise KeyError(f"Unknown series '{self.name}' in expression.") from exc


@dataclass(frozen=True)
class Literal(Expression):
    value: float

    def _collect_series(self, order: List[str], seen: Set[str]) -> None:
        # Literals do not contribute series references.
        return None

    def _to_placeholder(self, mapping: dict[str, int], parent_prec: int) -> str:
        if self.value.is_integer():
            return str(int(self.value))
        return repr(self.value)


@dataclass(frozen=True)
class UnaryOp(Expression):
    kind: str  # currently only "neg"
    operand: Expression

    def _collect_series(self, order: List[str], seen: Set[str]) -> None:
        self.operand._collect_series(order, seen)

    def _to_placeholder(self, mapping: dict[str, int], parent_prec: int) -> str:
        prec = _PREC["neg"]
        inner = self.operand._to_placeholder(mapping, prec)
        text = f"-{inner}"
        if prec < parent_prec:
            return f"({text})"
        return text


@dataclass(frozen=True)
class BinaryOp(Expression):
    kind: str  # "add", "sub", "mul", "div"
    left: Expression
    right: Expression

    def _collect_series(self, order: List[str], seen: Set[str]) -> None:
        self.left._collect_series(order, seen)
        self.right._collect_series(order, seen)

    def _to_placeholder(self, mapping: dict[str, int], parent_prec: int) -> str:
        symbol = _SYMBOL[self.kind]
        prec = _PREC[self.kind]

        left_text = self.left._to_placeholder(mapping, prec)
        right_prec = prec - 1 if self.kind in {"sub", "div"} else prec
        right_text = self.right._to_placeholder(mapping, right_prec)

        expr = f"{left_text} {symbol} {right_text}"
        if prec < parent_prec:
            return f"({expr})"
        return expr


_SYMBOL = {
    "add": "+",
    "sub": "-",
    "mul": "*",
    "div": "/",
}

_PREC = {
    "add": 1,
    "sub": 1,
    "mul": 2,
    "div": 2,
    "neg": 3,
}


