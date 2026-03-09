"""
Master container optimizer.

Adapted from the Inditex mic-packagingoptimization reference pipeline
(P1/P2/P3 Optimizer) to work with dynamic containers stored in MongoDB
instead of the hardcoded P1/P2/P3 catalog.

For each active container (sorted by priority ascending):
  1. Compute usable interior per axis:
       usable = dim_range - 2 × wall_cm - 2 × inner_margin_cm
     dims_cm are treated as EXTERIOR dimension ranges.
  2. Try all 6 orientations of the inner box exterior dims.
  3. For each orientation, sweep nL × nH × nW within usable limits.
     The container is sized to nX × innerX (≤ dim.max); if nX × innerX is
     below the minimum for that axis, the minimum size applies and the gap
     becomes void/air.
  4. Constrain inners_used by max_weight_kg.
  5. Score: fill_pct ↑  >  inners_used ↑  >  vol_usable ↓  (most compact).
  6. Accept the first container (by priority) whose air_pct ≤ max_air_pct.
  7. Return (selected_master, all_evaluated).
     If none accepted, selected is the highest fill_pct result with accepted=False.
"""

from __future__ import annotations

import math
from itertools import permutations
from typing import List, Optional, Tuple

from ..models.proposal import MasterResult

_EPS      = 1e-6   # minimum residual gap to bother filling
_FLAP_CM  = 1.0    # extra H reduction for container top-flap overlap


# ---------------------------------------------------------------------------
# Helper: best grid for a prismatic sub-space (used for extras filling)
# ---------------------------------------------------------------------------

def _best_grid_for_prism(
    Lp: float,
    Hp: float,
    Wp: float,
    inner_dims: Tuple[float, float, float],
) -> Optional[dict]:
    """
    Find the best (nL, nH, nW) grid of inner boxes that fits in the prism (Lp, Hp, Wp).
    Tries all 6 orientations of the inner box. Scores by count, then nH.
    Returns None if no orientation fits even a single inner.

    inner_dims is (max, med, min) — already sorted descending.
    """
    ax_labels = ["max", "med", "min"]
    dim_map = {"max": inner_dims[0], "med": inner_dims[1], "min": inner_dims[2]}
    best: Optional[dict] = None

    for perm in permutations(range(3)):
        axL, axH, axW = ax_labels[perm[0]], ax_labels[perm[1]], ax_labels[perm[2]]
        Lr = dim_map[axL]
        Hr = dim_map[axH]
        Wr = dim_map[axW]

        if Lr <= 0 or Hr <= 0 or Wr <= 0:
            continue

        nL = int(math.floor(Lp / Lr))
        nH = int(math.floor(Hp / Hr))
        nW = int(math.floor(Wp / Wr))

        if nL == 0 or nH == 0 or nW == 0:
            continue

        count = nL * nH * nW
        score = (count, nH)  # tie-break: prefer taller stacks
        if best is None or score > best["score"]:
            best = {
                "score": score,
                "grid": (nL, nH, nW),
                "inner_rot": (round(Lr, 4), round(Hr, 4), round(Wr, 4)),
                "inner_axes": (axL, axH, axW),
            }

    return best


# ---------------------------------------------------------------------------
# Single-container evaluator
# ---------------------------------------------------------------------------

def _evaluate_container(
    container: dict,
    inner_ext: Tuple[float, float, float],
    inner_weight_kg: float,
) -> Optional[MasterResult]:
    """
    Find the best grid (nL × nH × nW) of inner boxes that fits in this container.
    Returns None if the inner box does not fit in the container at all.

    container dims_cm are EXTERIOR ranges.
    Usable interior per axis = dim - 2×wall_cm - 2×margin.
    """
    wall_cm   = container["wall_thickness_mm"] / 10.0
    margin_l  = container["inner_margin_cm"]["length"]
    margin_h  = container["inner_margin_cm"]["height"]
    margin_w  = container["inner_margin_cm"]["width"]

    # Usable interior space after discounting wall + operational margin
    UL_min = max(0.0, container["dims_cm"]["length"]["min"] - 2 * wall_cm - 2 * margin_l)
    UL_max = max(0.0, container["dims_cm"]["length"]["max"] - 2 * wall_cm - 2 * margin_l)
    UH_min = max(0.0, container["dims_cm"]["height"]["min"] - 2 * wall_cm - 2 * margin_h - _FLAP_CM)
    UH_max = max(0.0, container["dims_cm"]["height"]["max"] - 2 * wall_cm - 2 * margin_h - _FLAP_CM)
    UW_min = max(0.0, container["dims_cm"]["width"]["min"]  - 2 * wall_cm - 2 * margin_w)
    UW_max = max(0.0, container["dims_cm"]["width"]["max"]  - 2 * wall_cm - 2 * margin_w)

    max_kg = container["max_weight_kg"]

    # inner_ext is already sorted descending (max ≥ med ≥ min)
    dim_map   = {"max": inner_ext[0], "med": inner_ext[1], "min": inner_ext[2]}
    ax_labels = ["max", "med", "min"]

    best: Optional[dict] = None

    for perm in permutations(range(3)):
        axL, axH, axW = ax_labels[perm[0]], ax_labels[perm[1]], ax_labels[perm[2]]
        Lr = dim_map[axL]
        Hr = dim_map[axH]
        Wr = dim_map[axW]

        if Lr <= 0 or Hr <= 0 or Wr <= 0:
            continue

        max_nL = int(math.floor(UL_max / Lr))
        max_nH = int(math.floor(UH_max / Hr))
        max_nW = int(math.floor(UW_max / Wr))

        if max_nL == 0 or max_nH == 0 or max_nW == 0:
            continue

        for nL in range(1, max_nL + 1):
            need_L = nL * Lr
            if need_L > UL_max:
                break
            # If the row of inners is shorter than container minimum, the
            # container is still built at its minimum — gap is void/air.
            use_L = max(need_L, UL_min)

            for nH in range(1, max_nH + 1):
                need_H = nH * Hr
                if need_H > UH_max:
                    break
                use_H = max(need_H, UH_min)

                for nW in range(1, max_nW + 1):
                    need_W = nW * Wr
                    if need_W > UW_max:
                        break
                    use_W = max(need_W, UW_min)

                    count = nL * nH * nW

                    # Weight constraint
                    max_by_weight = (
                        int(math.floor(max_kg / inner_weight_kg))
                        if inner_weight_kg > 0
                        else count
                    )
                    inners_used = min(count, max_by_weight)

                    # Volume metrics
                    vol_unit    = inner_ext[0] * inner_ext[1] * inner_ext[2]
                    vol_usable  = use_L * use_H * use_W
                    fill_pct    = (
                        round(min(100.0, inners_used * vol_unit / vol_usable * 100.0), 2)
                        if vol_usable > 0 else 0.0
                    )
                    air_pct = round(100.0 - fill_pct, 2)

                    # Exterior dims of this specific container instance
                    ext_L = round(need_L + 2 * wall_cm + 2 * margin_l, 4)
                    ext_H = round(need_H + 2 * wall_cm + 2 * margin_h, 4)
                    ext_W = round(need_W + 2 * wall_cm + 2 * margin_w, 4)

                    # Score: fill ↑  >  inners ↑  >  volume ↓
                    score = (fill_pct, inners_used, -vol_usable)

                    if best is None or score > best["score"]:
                        best = {
                            "score": score,
                            "grid": [nL, nH, nW],
                            "inner_dims_rotated": [
                                round(Lr, 4), round(Hr, 4), round(Wr, 4)
                            ],
                            "inner_axes_used": [axL, axH, axW],
                            "util_dims": [
                                round(use_L, 4), round(use_H, 4), round(use_W, 4)
                            ],
                            "ext_dims": [ext_L, ext_H, ext_W],
                            "fill_pct": fill_pct,
                            "air_pct": air_pct,
                            "inners_used": inners_used,
                            "max_by_weight": max_by_weight,
                            "total_weight_kg": round(
                                inners_used * inner_weight_kg, 4
                            ),
                        }

    if best is None:
        return None

    # -----------------------------------------------------------------------
    # Extras: fill residual frontal (L gap) and side (W gap) prismas
    # -----------------------------------------------------------------------
    use_L, use_H, use_W = best["util_dims"]
    Lr, Hr, Wr          = best["inner_dims_rotated"]
    nL, nH, nW          = best["grid"]

    resL = max(use_L - nL * Lr, 0.0)   # gap along L
    resW = max(use_W - nW * Wr, 0.0)   # gap along W

    inners_used_final = best["inners_used"]
    weight_cap_left   = max(0, best["max_by_weight"] - inners_used_final)
    extras: List[dict] = []

    # 1) Frontal prisma: (resL, use_H, use_W) at offset (nL×Lr, 0, 0)
    if weight_cap_left > 0 and resL > _EPS:
        cand = _best_grid_for_prism(resL, use_H, use_W, inner_ext)
        if cand:
            pieces = cand["grid"][0] * cand["grid"][1] * cand["grid"][2]
            add    = min(pieces, weight_cap_left)
            if add > 0:
                extras.append({
                    "kind": "front",
                    "grid":       list(cand["grid"]),
                    "inner_rot":  list(cand["inner_rot"]),
                    "inner_axes": list(cand["inner_axes"]),
                    "offset":     [round(nL * Lr, 4), 0.0, 0.0],
                })
                inners_used_final += add
                weight_cap_left   -= add

    # 2) Side prisma: (use_L, use_H, resW) at offset (0, 0, nW×Wr)
    if weight_cap_left > 0 and resW > _EPS:
        cand = _best_grid_for_prism(use_L, use_H, resW, inner_ext)
        if cand:
            pieces = cand["grid"][0] * cand["grid"][1] * cand["grid"][2]
            add    = min(pieces, weight_cap_left)
            if add > 0:
                extras.append({
                    "kind": "side",
                    "grid":       list(cand["grid"]),
                    "inner_rot":  list(cand["inner_rot"]),
                    "inner_axes": list(cand["inner_axes"]),
                    "offset":     [0.0, 0.0, round(nW * Wr, 4)],
                })
                inners_used_final += add
                weight_cap_left   -= add

    # Recalculate metrics using the full rotated inner volume
    vol_unit       = Lr * Hr * Wr
    vol_usable     = use_L * use_H * use_W
    fill_pct_final = round(
        min(100.0, inners_used_final * vol_unit / vol_usable * 100.0), 2
    ) if vol_usable > 0 else 0.0
    air_pct_final  = round(100.0 - fill_pct_final, 2)

    return MasterResult(
        container_id=container["id"],
        container_name=container["name"],
        inners_used=inners_used_final,
        max_by_weight=best["max_by_weight"],
        grid=best["grid"],
        inner_dims_rotated=best["inner_dims_rotated"],
        inner_axes_used=best["inner_axes_used"],
        util_dims=best["util_dims"],
        ext_dims=best["ext_dims"],
        fill_pct=fill_pct_final,
        air_pct=air_pct_final,
        total_weight_kg=round(inners_used_final * inner_weight_kg, 4),
        accepted=False,  # determined by the pipeline selector below
        extras=extras if extras else None,
    )


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def run_master_pipeline(
    inner_ext: Tuple[float, float, float],
    inner_weight_kg: float,
    containers: List[dict],
) -> Tuple[Optional[MasterResult], List[MasterResult]]:
    """
    Evaluate all active containers in priority order and select the best proposal.

    Accepts the *first* container (lowest priority number) whose
    air_pct ≤ container.max_air_pct.  All containers are evaluated
    regardless so the reviewer can compare options.

    Returns (selected_master, all_evaluated).
    selected_master.accepted == True  →  a viable container was found.
    selected_master.accepted == False →  no container met its threshold;
                                         best available is returned anyway.
    """
    all_results: List[MasterResult] = []
    selected: Optional[MasterResult] = None

    for container in containers:
        result = _evaluate_container(container, inner_ext, inner_weight_kg)
        if result is None:
            continue  # inner box doesn't physically fit in this container

        max_air = container.get("max_air_pct", 5.0)
        if selected is None and result.air_pct <= max_air:
            result = result.model_copy(update={"accepted": True})
            selected = result

        all_results.append(result)

    # If no container met its threshold, return the best available (accepted=False)
    if selected is None and all_results:
        best_idx = max(range(len(all_results)), key=lambda i: all_results[i].fill_pct)
        selected = all_results[best_idx]

    return selected, all_results
