"""
Inner box calculator.

Given the packaged article dimensions and lot_size (the indivisible distribution
lot — how many articles go into one inner box), computes the most compact valid
inner box configuration.

Strategy
--------
The inner box must hold exactly lot_size articles (no partial fill).
Steps:
  1. Sort article dims → (d_max ≥ d_med ≥ d_min).
  2. Try all 6 orientations of the article (permutations of its 3 dims).
     De-duplicate orientations when two article sides are equal.
  3. For each orientation (Lr, Wr, Hr), enumerate all 3-factor partitions of
     lot_size:  nA × nB × nC = lot_size  (canonical: nA ≥ nB ≥ nC ≥ 1).
  4. Try all 6 orderings of (nA, nB, nC) assigned to (nL, nW, nH).
  5. Inner box dims = (nL*Lr, nW*Wr, nH*Hr).  Volume is always constant
     (N × article_vol), so rank by shape:
       primary  : minimize max(IL, IW, IH)  — most cubic
       secondary: minimize surface area      — tiebreak
  6. Sort the winning inner dims descending (max ≥ med ≥ min) so the master
     optimizer can treat them as axis-agnostic.

Complexity: O(d(N) × 36) where d(N) is the number of divisors of N (~≤ 100
     for any practical lot_size). Always fast.
"""

from __future__ import annotations

from itertools import permutations
from typing import Optional

from ..models.proposal import InnerBoxCalc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _factorizations_3(n: int):
    """
    Yield all canonical triples (a, b, c) with a ≥ b ≥ c ≥ 1 and a*b*c == n.

    Iteration:
      c from 1 to ⌊n^(1/3)⌋
        b from c to ⌊√(n/c)⌋
          a = n/(b*c)  if divisible
    """
    c = 1
    while c * c * c <= n:
        if n % c == 0:
            rem = n // c          # a * b = rem,  need a ≥ b ≥ c
            b = c
            while b * b <= rem:
                if rem % b == 0:
                    a = rem // b  # a ≥ b because b² ≤ rem ⟹ b ≤ √(a·b) ⟹ b ≤ a
                    yield (a, b, c)
                b += 1
        c += 1


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_inner_box(
    length_cm: float,
    width_cm: float,
    height_cm: float,
    weight_kg: float,
    lot_size: int,
    wall_thickness_mm: float = 3.0,
    constraints: Optional[dict] = None,
) -> Optional[InnerBoxCalc]:
    """
    Compute the most compact inner box that holds exactly `lot_size` articles.

    Returns an InnerBoxCalc with sides sorted descending, or None if
    lot_size < 1 (should not happen given model validation).

    constraints (optional):
      orientation_locked: bool   - if True, restrict how the article sits in the inner box
      locked_axis: str|None      - "height"→article max dim must be on H slot
                                   "width" →article min dim must be on H slot (lying flat)
                                   "length"→article med dim on H slot
                                   None   → only natural orientation (max→L, med→W, min→H)
    """
    if lot_size < 1:
        return None

    # 1) Sort article dims descending → axis labels "max", "med", "min"
    d_sorted = sorted([length_cm, width_cm, height_cm], reverse=True)
    ax_names = ["max", "med", "min"]

    # Build set of allowed article orientations based on constraints.
    # The tuple (perm[0], perm[1], perm[2]) maps d_sorted axes to (L, W, H) slots.
    # locked_axis refers to the H slot (index 1 in (nL,nW,nH) triple of the grid,
    # but H of the article orientation is perm[2]):
    #   "height" -> article max dim (index 0) must be in H slot -> perm[2] == 0
    #   "width"  -> article min dim (index 2) must be in H slot -> perm[2] == 2
    #   "length" -> article med dim (index 1) must be in H slot -> perm[2] == 1
    #   None     -> lock to natural (0,1,2) only
    allowed_art_perms: Optional[set] = None
    if constraints and constraints.get("orientation_locked"):
        locked_axis = constraints.get("locked_axis")
        if locked_axis == "height":
            allowed_art_perms = {p for p in permutations(range(3)) if p[2] == 0}
        elif locked_axis == "width":
            allowed_art_perms = {p for p in permutations(range(3)) if p[2] == 2}
        elif locked_axis == "length":
            allowed_art_perms = {p for p in permutations(range(3)) if p[2] == 1}
        else:
            allowed_art_perms = {(0, 1, 2)}

    best_result: Optional[InnerBoxCalc] = None
    best_score: Optional[tuple] = None

    tried_orientations: set = set()

    # 2) Try all 6 article orientations
    for perm in permutations(range(3)):
        if allowed_art_perms is not None and perm not in allowed_art_perms:
            continue
        Lr = d_sorted[perm[0]]
        Wr = d_sorted[perm[1]]
        Hr = d_sorted[perm[2]]

        key = (Lr, Wr, Hr)
        if key in tried_orientations:
            continue
        tried_orientations.add(key)

        axes = (ax_names[perm[0]], ax_names[perm[1]], ax_names[perm[2]])

        # 3–4) Enumerate 3-factor partitions; try all assignments to (nL, nW, nH)
        for (a, b, c) in _factorizations_3(lot_size):
            for (nL, nW, nH) in set(permutations([a, b, c])):
                IL = nL * Lr
                IW = nW * Wr
                IH = nH * Hr

                # 5) Score: minimize max dim first, then surface (most cubic)
                score = (
                    round(max(IL, IW, IH), 6),
                    round(2.0 * (IL * IW + IL * IH + IW * IH), 6),
                )

                if best_score is None or score < best_score:
                    best_score = score

                    # 6) Sort resulting inner dims descending
                    sides = sorted(
                        [
                            (IL, nL, axes[0]),
                            (IW, nW, axes[1]),
                            (IH, nH, axes[2]),
                        ],
                        key=lambda x: x[0],
                        reverse=True,
                    )

                    wall_cm = wall_thickness_mm / 10.0
                    best_result = InnerBoxCalc(
                        wall_thickness_mm=wall_thickness_mm,
                        int_max_cm=round(sides[0][0], 4),
                        int_med_cm=round(sides[1][0], 4),
                        int_min_cm=round(sides[2][0], 4),
                        ext_max_cm=round(sides[0][0] + 2 * wall_cm, 4),
                        ext_med_cm=round(sides[1][0] + 2 * wall_cm, 4),
                        ext_min_cm=round(sides[2][0] + 2 * wall_cm, 4),
                        total_weight_kg=round(lot_size * weight_kg, 4),
                        grid=[sides[0][1], sides[1][1], sides[2][1]],
                        article_axes_per_inner_axis=[
                            sides[0][2], sides[1][2], sides[2][2]
                        ],
                    )

    return best_result
