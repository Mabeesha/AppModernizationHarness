"""Check registration and the execution context handed to every check."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable

from .model import CheckResult, Document, InstructionSet
from .tokens import TokenCounter


@dataclass
class Context:
    """Everything a check may read. Checks must not touch the filesystem directly."""

    iset: InstructionSet
    repo_root: Path
    counter: TokenCounter
    # Generated artifacts from a real pipeline run (--docs). Empty when not supplied;
    # checks that need them report `skipped` rather than estimating.
    docs: list[Document] = field(default_factory=list)
    # Gate for checks needing a judge call (Phase 3+ of the design).
    with_llm: bool = False
    include_experimental: bool = False
    config: dict = field(default_factory=dict)

    def doc_by_name(self, name: str) -> Document | None:
        return self.iset.by_name(name) or next(
            (d for d in self.docs if d.name == name), None
        )


CheckFn = Callable[[Context], CheckResult]


@dataclass(frozen=True)
class Check:
    id: str
    group: str
    title: str
    fn: CheckFn
    deterministic: bool = True
    experimental: bool = False
    implemented: bool = True


_REGISTRY: dict[str, Check] = {}


def check(
    check_id: str,
    title: str,
    *,
    deterministic: bool = True,
    experimental: bool = False,
    implemented: bool = True,
):
    """Decorator registering a check under its design-document ID (A1, B3, ...)."""

    def wrap(fn: CheckFn) -> CheckFn:
        if check_id in _REGISTRY:
            raise ValueError(f"duplicate check id: {check_id}")
        _REGISTRY[check_id] = Check(
            id=check_id,
            group=check_id[0].upper(),
            title=title,
            fn=fn,
            deterministic=deterministic,
            experimental=experimental,
            implemented=implemented,
        )
        return fn

    return wrap


def all_checks() -> list[Check]:
    def sort_key(c: Check) -> tuple[str, int]:
        return (c.group, int(c.id[1:]) if c.id[1:].isdigit() else 0)

    return sorted(_REGISTRY.values(), key=sort_key)


def select(
    selectors: Iterable[str] | None,
    *,
    det_only: bool = False,
    include_experimental: bool = False,
) -> list[Check]:
    """Resolve --checks selectors. Accepts groups ('A') and ids ('A1').

    Raises ValueError on a selector that matches nothing. Silently running zero
    checks and exiting 0 would let a typo in CI read as a passing run.
    """
    chosen = all_checks()

    if selectors:
        wanted = {s.strip().upper() for s in selectors if s.strip()}
        known_ids = {c.id.upper() for c in chosen}
        known_groups = {c.group for c in chosen}
        unknown = sorted(wanted - known_ids - known_groups)
        if unknown:
            raise ValueError(
                f"unknown check selector(s): {', '.join(unknown)}. "
                f"Valid ids: {', '.join(sorted(known_ids))}; "
                f"valid groups: {', '.join(sorted(known_groups))}"
            )
        chosen = [
            c for c in chosen
            if c.id.upper() in wanted or c.group in wanted
        ]

    if det_only:
        chosen = [c for c in chosen if c.deterministic]
    if not include_experimental:
        chosen = [c for c in chosen if not c.experimental]

    return chosen


def load_builtin_checks() -> None:
    """Import check modules for their registration side effects."""
    from .checks import (  # noqa: F401
        size,
        references,
        coherence,
        consistency,
        conflicts,
        hygiene,
        style,
    )
