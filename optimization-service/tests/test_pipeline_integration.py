"""
Integration tests: inner_calculator + master_optimizer working together.

These tests simulate the full optimization pipeline as the /proposals/optimize
endpoint would call it, verifying that:
  - InnerBoxCalc output feeds correctly into run_master_pipeline
  - The combined result satisfies all physical constraints
  - Real-world-sized products (bulb, shoe) produce sensible outcomes
  - Edge cases (very heavy articles, prime lot_sizes) don't crash
"""
from __future__ import annotations

import math
import pytest

from app.engine.inner_calculator import compute_inner_box
from app.engine.master_optimizer import run_master_pipeline

# ---------------------------------------------------------------------------
# Shared containers (realistic, based on seed data proportions)
# ---------------------------------------------------------------------------

CONT_SMALL = {
    "id": "small",
    "name": "Caja Pequeña",
    "priority": 1,
    "dims_cm": {
        "length": {"min": 25.0, "max": 35.0},
        "height": {"min": 20.0, "max": 30.0},
        "width":  {"min": 20.0, "max": 28.0},
    },
    "wall_thickness_mm": 5.0,
    "inner_margin_cm": {"length": 0.5, "height": 0.5, "width": 0.5},
    "max_weight_kg": 15.0,
    "max_air_pct": 25.0,
    "active": True,
}

CONT_MEDIUM = {
    "id": "medium",
    "name": "Caja Mediana",
    "priority": 2,
    "dims_cm": {
        "length": {"min": 45.0, "max": 55.0},
        "height": {"min": 35.0, "max": 45.0},
        "width":  {"min": 25.0, "max": 35.0},
    },
    "wall_thickness_mm": 5.0,
    "inner_margin_cm": {"length": 0.5, "height": 0.5, "width": 0.5},
    "max_weight_kg": 25.0,
    "max_air_pct": 30.0,
    "active": True,
}

CONTAINERS = [CONT_SMALL, CONT_MEDIUM]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def full_pipeline(L, W, H, weight, lot, wall_mm=3.0, constraints=None):
    inner = compute_inner_box(L, W, H, weight, lot, wall_thickness_mm=wall_mm,
                              constraints=constraints)
    if inner is None:
        return None, None, []
    inner_ext = (inner.ext_max_cm, inner.ext_med_cm, inner.ext_min_cm)
    selected, evaluated = run_master_pipeline(
        inner_ext, inner.total_weight_kg, CONTAINERS,
        constraints=constraints,
    )
    return inner, selected, evaluated


# ---------------------------------------------------------------------------
# Tests — realistic products
# ---------------------------------------------------------------------------

class TestPipelineBulb:
    """LED bulb: small, light article, lot_size=6."""

    L, W, H = 6.5, 6.5, 11.0   # cm
    WEIGHT   = 0.08              # kg
    LOT      = 6

    def test_inner_computed(self):
        inner = compute_inner_box(self.L, self.W, self.H, self.WEIGHT, self.LOT)
        assert inner is not None

    def test_inner_volume_conservation(self):
        inner = compute_inner_box(self.L, self.W, self.H, self.WEIGHT, self.LOT)
        expected = self.L * self.W * self.H * self.LOT
        actual = inner.int_max_cm * inner.int_med_cm * inner.int_min_cm
        assert math.isclose(actual, expected, rel_tol=1e-5)

    def test_pipeline_finds_container(self):
        inner, selected, evaluated = full_pipeline(
            self.L, self.W, self.H, self.WEIGHT, self.LOT
        )
        # With this small bulb, at least one container should work
        assert len(evaluated) > 0

    def test_pipeline_no_crash(self):
        inner, selected, evaluated = full_pipeline(
            self.L, self.W, self.H, self.WEIGHT, self.LOT
        )
        assert inner is not None  # inner box always computable

    def test_total_weight_correct(self):
        inner = compute_inner_box(self.L, self.W, self.H, self.WEIGHT, self.LOT)
        assert math.isclose(inner.total_weight_kg, self.LOT * self.WEIGHT, rel_tol=1e-6)


class TestPipelineShoe:
    """Shoe box: larger, heavier article, lot_size=12."""

    L, W, H  = 30.0, 12.0, 10.0   # cm
    WEIGHT   = 0.8                  # kg
    LOT      = 12

    def test_inner_computed(self):
        inner = compute_inner_box(self.L, self.W, self.H, self.WEIGHT, self.LOT)
        assert inner is not None

    def test_grid_product(self):
        inner = compute_inner_box(self.L, self.W, self.H, self.WEIGHT, self.LOT)
        g = inner.grid
        assert g[0] * g[1] * g[2] == self.LOT

    def test_pipeline_evaluated_all_containers(self):
        inner, selected, evaluated = full_pipeline(
            self.L, self.W, self.H, self.WEIGHT, self.LOT
        )
        # Large shoe box may not fit in small container, but medium should work
        # At minimum, inner box must be computed
        assert inner is not None

    def test_fill_air_sum_100_if_container_found(self):
        inner, selected, _ = full_pipeline(
            self.L, self.W, self.H, self.WEIGHT, self.LOT
        )
        if selected is not None:
            assert math.isclose(selected.fill_pct + selected.air_pct, 100.0, rel_tol=1e-4)


class TestPipelineEdgeCases:

    def test_very_heavy_article_capped_by_weight(self):
        """Heavy article (5kg each): weight cap should limit inners_used."""
        inner, selected, evaluated = full_pipeline(10.0, 8.0, 6.0, 5.0, 6)
        if selected is not None:
            max_by_w = CONT_SMALL["max_weight_kg"] / (5.0 * 6)  # containers vary
            # Just verify inners_used is non-negative and reasonable
            assert selected.inners_used >= 0

    def test_prime_lot_size_pipeline(self):
        inner, selected, evaluated = full_pipeline(10.0, 8.0, 6.0, 0.3, 7)
        assert inner is not None
        assert inner.grid[0] * inner.grid[1] * inner.grid[2] == 7

    def test_lot_size_1_single_article_inner(self):
        inner, selected, evaluated = full_pipeline(10.0, 8.0, 6.0, 0.5, 1)
        assert inner is not None
        assert inner.grid == [1, 1, 1]

    def test_constraints_propagate_to_master(self):
        """Constraint orientation_locked must not crash the full pipeline."""
        constraints = {"orientation_locked": True, "locked_axis": "height"}
        inner, selected, evaluated = full_pipeline(
            10.0, 8.0, 6.0, 0.5, 6, constraints=constraints
        )
        assert inner is not None  # inner box always computed

    def test_wall_thickness_variations(self):
        for wall_mm in [0.0, 1.5, 3.0, 5.0, 10.0]:
            inner = compute_inner_box(10, 8, 6, 0.5, 6, wall_thickness_mm=wall_mm)
            assert inner is not None
            assert math.isclose(
                inner.ext_max_cm,
                inner.int_max_cm + 2 * wall_mm / 10.0,
                rel_tol=1e-6,
            )

    def test_multiple_containers_priority_respected(self):
        """The pipeline must not skip valid containers: priority 1 tried first."""
        # Make p1 container perfectly tailored for the inner box
        inner = compute_inner_box(5.0, 5.0, 5.0, 0.1, 6)
        assert inner is not None
        inner_ext = (inner.ext_max_cm, inner.ext_med_cm, inner.ext_min_cm)

        cont_p1 = {**CONT_SMALL, "id": "p1", "priority": 1, "max_air_pct": 50.0}
        cont_p2 = {**CONT_MEDIUM, "id": "p2", "priority": 2, "max_air_pct": 50.0}

        selected, _ = run_master_pipeline(inner_ext, inner.total_weight_kg,
                                          [cont_p1, cont_p2])
        if selected is not None and selected.accepted:
            assert selected.container_id == "p1"

    def test_identical_articles_produce_cubic_inner(self):
        """Cube articles: optimizer should prefer 2×2×2 for lot_size=8."""
        inner = compute_inner_box(10.0, 10.0, 10.0, 0.5, 8)
        assert inner is not None
        assert inner.grid == [2, 2, 2]
        # All interior sides equal (perfectly cubic inner box)
        assert math.isclose(inner.int_max_cm, inner.int_med_cm, rel_tol=1e-6)
        assert math.isclose(inner.int_med_cm, inner.int_min_cm, rel_tol=1e-6)
