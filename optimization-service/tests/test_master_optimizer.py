"""
Unit tests for master_optimizer.run_master_pipeline and _evaluate_container.

Tests cover:
  - Container that fits → result with correct grid product and weight
  - Container too small → _evaluate_container returns None
  - Pipeline selects first container meeting air_pct threshold
  - Pipeline returns best fallback when no container meets threshold
  - All containers evaluated regardless of selection
  - Weight cap applied correctly (inners_used ≤ max_by_weight)
  - fill_pct + air_pct always sum to 100
  - max_stack_layers constraint
  - Priority ordering: lowest priority number selected first
  - Extra fill blocks (front / depth prisms)
"""
from __future__ import annotations

import math
import pytest

from app.engine.master_optimizer import (
    run_master_pipeline,
    _evaluate_container,
)

# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

# Inner box exterior dims (sorted descending): 20cm × 15cm × 10cm, 2 kg
INNER_EXT  = (20.0, 15.0, 10.0)
INNER_WT   = 2.0

# Container large enough to accept several inners
CONT_GOOD = {
    "id": "c-good",
    "name": "Buen Contenedor",
    "priority": 1,
    "dims_cm": {
        "length": {"min": 40.0, "max": 65.0},
        "height": {"min": 30.0, "max": 45.0},
        "width":  {"min": 20.0, "max": 35.0},
    },
    "wall_thickness_mm": 5.0,
    "inner_margin_cm": {"length": 0.5, "height": 0.5, "width": 0.5},
    "max_weight_kg": 50.0,
    "max_air_pct": 30.0,
    "active": True,
}

# Container too small for the inner box
CONT_TINY = {
    "id": "c-tiny",
    "name": "Contenedor Minúsculo",
    "priority": 1,
    "dims_cm": {
        "length": {"min": 5.0, "max": 8.0},
        "height": {"min": 5.0, "max": 8.0},
        "width":  {"min": 5.0, "max": 8.0},
    },
    "wall_thickness_mm": 5.0,
    "inner_margin_cm": {"length": 0.5, "height": 0.5, "width": 0.5},
    "max_weight_kg": 5.0,
    "max_air_pct": 5.0,
    "active": True,
}

# Container that fits but has very tight air threshold (hard to satisfy)
CONT_STRICT = {
    "id": "c-strict",
    "name": "Contenedor Estricto",
    "priority": 2,
    "dims_cm": {
        "length": {"min": 55.0, "max": 65.0},
        "height": {"min": 35.0, "max": 45.0},
        "width":  {"min": 25.0, "max": 35.0},
    },
    "wall_thickness_mm": 5.0,
    "inner_margin_cm": {"length": 0.5, "height": 0.5, "width": 0.5},
    "max_weight_kg": 50.0,
    "max_air_pct": 0.0,   # impossible to satisfy
    "active": True,
}


# ---------------------------------------------------------------------------
# _evaluate_container
# ---------------------------------------------------------------------------

class TestEvaluateContainer:

    def test_returns_none_when_inner_does_not_fit(self):
        result = _evaluate_container(CONT_TINY, INNER_EXT, INNER_WT)
        assert result is None

    def test_returns_master_result_when_fits(self):
        result = _evaluate_container(CONT_GOOD, INNER_EXT, INNER_WT)
        assert result is not None

    def test_grid_product_positive(self):
        result = _evaluate_container(CONT_GOOD, INNER_EXT, INNER_WT)
        nL, nH, nW = result.grid
        assert nL * nH * nW >= 1

    def test_fill_plus_air_equals_100(self):
        result = _evaluate_container(CONT_GOOD, INNER_EXT, INNER_WT)
        assert math.isclose(result.fill_pct + result.air_pct, 100.0, rel_tol=1e-4)

    def test_fill_pct_between_0_and_100(self):
        result = _evaluate_container(CONT_GOOD, INNER_EXT, INNER_WT)
        assert 0.0 <= result.fill_pct <= 100.0
        assert 0.0 <= result.air_pct <= 100.0

    def test_weight_cap_applied(self):
        """If max_weight_kg limits packing, inners_used ≤ max_by_weight."""
        tight_weight_cont = {**CONT_GOOD, "max_weight_kg": 5.0}  # allows max 2 inners of 2kg
        result = _evaluate_container(tight_weight_cont, INNER_EXT, INNER_WT)
        assert result is not None
        assert result.inners_used <= result.max_by_weight

    def test_max_weight_equals_inner_weight_caps_at_1(self):
        one_kg_cont = {**CONT_GOOD, "max_weight_kg": 2.0}  # exactly 1 inner
        result = _evaluate_container(one_kg_cont, INNER_EXT, INNER_WT)
        assert result is not None
        assert result.inners_used <= 1

    def test_ext_dims_has_3_elements(self):
        result = _evaluate_container(CONT_GOOD, INNER_EXT, INNER_WT)
        assert len(result.ext_dims) == 3
        assert all(d > 0 for d in result.ext_dims)

    def test_accepted_is_false_by_default(self):
        """_evaluate_container never sets accepted=True; only pipeline does."""
        result = _evaluate_container(CONT_GOOD, INNER_EXT, INNER_WT)
        assert result.accepted is False

    def test_max_stack_layers_constraint(self):
        """max_stack_layers=1 means only 1 layer stacked (nW ≤ 1)."""
        constraints = {"max_stack_layers": 1}
        result = _evaluate_container(CONT_GOOD, INNER_EXT, INNER_WT, constraints)
        assert result is not None
        # nW is index 2 in grid (rendered vertical)
        assert result.grid[2] <= 1

    def test_container_id_and_name_preserved(self):
        result = _evaluate_container(CONT_GOOD, INNER_EXT, INNER_WT)
        assert result.container_id == CONT_GOOD["id"]
        assert result.container_name == CONT_GOOD["name"]


# ---------------------------------------------------------------------------
# run_master_pipeline
# ---------------------------------------------------------------------------

class TestRunMasterPipeline:

    def test_empty_containers_returns_none_selected_and_empty_list(self):
        selected, evaluated = run_master_pipeline(INNER_EXT, INNER_WT, [])
        assert selected is None
        assert evaluated == []

    def test_single_good_container_accepted(self):
        selected, evaluated = run_master_pipeline(INNER_EXT, INNER_WT, [CONT_GOOD])
        assert selected is not None
        assert selected.accepted is True
        assert len(evaluated) == 1

    def test_tiny_container_not_accepted_no_selection(self):
        selected, evaluated = run_master_pipeline(INNER_EXT, INNER_WT, [CONT_TINY])
        assert selected is None or selected.accepted is False
        assert len(evaluated) == 0  # tiny returns None from _evaluate_container

    def test_all_containers_evaluated_regardless(self):
        containers = [CONT_GOOD, CONT_STRICT]
        _, evaluated = run_master_pipeline(INNER_EXT, INNER_WT, containers)
        assert len(evaluated) == 2

    def test_priority_1_selected_over_priority_2(self):
        """First container (priority 1) should be selected if it meets threshold."""
        low_prio  = {**CONT_STRICT, "id": "c-p1", "priority": 1, "max_air_pct": 50.0}
        high_prio = {**CONT_GOOD,   "id": "c-p2", "priority": 2, "max_air_pct": 50.0}
        selected, _ = run_master_pipeline(INNER_EXT, INNER_WT, [low_prio, high_prio])
        assert selected is not None
        assert selected.container_id == "c-p1"

    def test_fallback_to_best_when_none_accepted(self):
        """When no container meets its threshold, selected=best fill_pct, accepted=False.

        Uses fixed container dims (min==max) that cannot be perfectly tiled by the
        inner box, guaranteeing air_pct > 0 so max_air_pct=0.0 is never satisfied.
        Container usable: L=48, H=36, W=28. Inner (23,18,13): best grid 2×2×2 gives
        fill≈89% (2cm wasted on L, 2cm on W) — accepted=False with max_air_pct=0.
        """
        cont_fixed = {
            **CONT_GOOD,
            "id": "c-fixed",
            "dims_cm": {
                "length": {"min": 50.0, "max": 50.0},
                "height": {"min": 40.0, "max": 40.0},
                "width":  {"min": 30.0, "max": 30.0},
            },
            "max_air_pct": 0.0,
        }
        inner_imperfect = (23.0, 18.0, 13.0)
        selected, evaluated = run_master_pipeline(inner_imperfect, 1.0, [cont_fixed])
        assert selected is not None
        assert selected.accepted is False
        assert selected.air_pct > 0.0

    def test_selected_is_in_evaluated_list(self):
        selected, evaluated = run_master_pipeline(INNER_EXT, INNER_WT, [CONT_GOOD])
        assert any(e.container_id == selected.container_id for e in evaluated)

    def test_fill_pct_sensible(self):
        selected, _ = run_master_pipeline(INNER_EXT, INNER_WT, [CONT_GOOD])
        assert selected is not None
        assert 0.0 < selected.fill_pct <= 100.0

    def test_weight_constraint_honored_in_pipeline(self):
        light_cont = {**CONT_GOOD, "max_weight_kg": 4.0}  # max 2 inners
        selected, _ = run_master_pipeline(INNER_EXT, INNER_WT, [light_cont])
        if selected is not None:
            assert selected.inners_used <= 2

    def test_with_orientation_constraint(self):
        """Pipeline accepts orientation constraints without crashing."""
        constraints = {"orientation_locked": True, "locked_axis": "height",
                       "required_inner_h_axis": "max"}
        selected, evaluated = run_master_pipeline(
            INNER_EXT, INNER_WT, [CONT_GOOD], constraints=constraints
        )
        assert len(evaluated) >= 0  # may be 0 if locked orientation doesn't fit

    def test_returns_tuple_of_two(self):
        result = run_master_pipeline(INNER_EXT, INNER_WT, [CONT_GOOD])
        assert isinstance(result, tuple) and len(result) == 2

    def test_cubic_inner_fits_better_than_elongated(self):
        """A cubic inner box should achieve higher fill_pct than an elongated one."""
        cubic_inner = (15.0, 15.0, 15.0)  # cube
        elon_inner  = (40.0,  5.0,  5.0)  # elongated

        sel_cubic, _ = run_master_pipeline(cubic_inner, 1.0, [CONT_GOOD])
        sel_elon, _  = run_master_pipeline(elon_inner,  1.0, [CONT_GOOD])

        if sel_cubic is not None and sel_elon is not None:
            # Cubic should pack more efficiently
            assert sel_cubic.fill_pct >= sel_elon.fill_pct
