from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Set


@dataclass(frozen=True)
class ReactionDelta:
    added: Set[str]
    removed: Set[str]


def compute_reaction_delta(old_set: Iterable[str], new_set: Iterable[str]) -> ReactionDelta:
    old_s = set(old_set)
    new_s = set(new_set)
    return ReactionDelta(
        added=new_s - old_s,
        removed=old_s - new_s,
    )
