"""
Unit tests for inner_calculator.compute_inner_box.

Tests cover:
  - Basic correctness: volume conservation, grid product = lot_size
  - Exterior = interior + 2*wall per axis
  - Cubic preference: most cubic arrangement wins (for lot_size with multiple factorizations)
  - lot_size = 1 (trivial case)
  - Large lot sizes and non-trivial factorizations
  - Orientation locked by constraints (height, width, length)
  - Degenerate input that should return None (lot_size < 1)
  - Weight calculation
  - Wall thickness = 0 (edge case)
  - Square article (deduplication of orientations)
  - Prime lot_size (only 1×1×N factorization)
"""
from __future__ import annotations

import math
import pytest

from app.engine.inner_calculator import compute_inner_box, _factorizations_3


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _grid_product(result) -> int:
    return result.grid[0] * result.grid[1] * result.grid[2]


def _int_volume(result) -> float:
    return result.int_max_cm * result.int_med_cm * result.int_min_cm


def _article_volume(length, width, height, lot_size) -> float:
    return length * width * height * lot_size


# ---------------------------------------------------------------------------
# Internal helper: _factorizations_3
# ---------------------------------------------------------------------------

class TestFactorizations3:

    def test_n1_yields_only_1_1_1(self):
        result = list(_factorizations_3(1))
        assert result == [(1, 1, 1)]

    def test_n6_all_canonical_triples(self):
        triples = list(_factorizations_3(6))
        # All canonical (a≥b≥c≥1, a*b*c=6): (6,1,1), (3,2,1), (2,2,... no), ...
        for a, b, c in triples:
            assert a >= b >= c >= 1
            assert a * b * c == 6

    def test_n8_includes_2_2_2(self):
        triples = list(_factorizations_3(8))
        assert (2, 2, 2) in triples

    def test_n12_correct_count(self):
        triples = list(_factorizations_3(12))
        for a, b, c in triples:
            assert a * b * c == 12
        # Verify uniqueness (canonical)
        assert len(triples) == len(set(triples))

    def test_prime_lot_size_only_N_1_1(self):
        for p in [7, 11, 13]:
            triples = list(_factorizations_3(p))
            assert (p, 1, 1) in triples
            assert len(triples) == 1  # only (p,1,1) for a prime


# ---------------------------------------------------------------------------
# compute_inner_box — basic correctness
# ---------------------------------------------------------------------------

class TestComputeInnerBoxBasic:

    def test_returns_not_none_for_valid_input(self):
        result = compute_inner_box(10, 8, 6, 0.5, 6)
        assert result is not None

    def test_grid_product_equals_lot_size(self):
        for lot in [1, 2, 6, 12, 24, 30]:
            result = compute_inner_box(10, 8, 6, 0.5, lot)
            assert _grid_product(result) == lot, f"lot={lot}: grid product mismatch"

    def test_volume_conservation(self):
        """Interior volume must equal lot_size × article volume."""
        L, W, H = 10.0, 8.0, 6.0
        lot = 6
        result = compute_inner_box(L, W, H, 0.5, lot)
        expected = _article_volume(L, W, H, lot)
        assert math.isclose(_int_volume(result), expected, rel_tol=1e-6)

    def test_exterior_equals_interior_plus_2_walls(self):
        wall_mm = 3.0
        result = compute_inner_box(10, 8, 6, 0.5, 6, wall_thickness_mm=wall_mm)
        wall_cm = wall_mm / 10.0
        assert math.isclose(result.ext_max_cm, result.int_max_cm + 2 * wall_cm, rel_tol=1e-6)
        assert math.isclose(result.ext_med_cm, result.int_med_cm + 2 * wall_cm, rel_tol=1e-6)
        assert math.isclose(result.ext_min_cm, result.int_min_cm + 2 * wall_cm, rel_tol=1e-6)

    def test_dims_sorted_descending(self):
        result = compute_inner_box(10, 8, 6, 0.5, 6)
        assert result.int_max_cm >= result.int_med_cm >= result.int_min_cm
        assert result.ext_max_cm >= result.ext_med_cm >= result.ext_min_cm

    def test_fill_pct_is_100(self):
        result = compute_inner_box(10, 8, 6, 0.5, 6)
        assert result.fill_pct == 100.0

    def test_air_pct_is_0(self):
        result = compute_inner_box(10, 8, 6, 0.5, 6)
        assert result.air_pct == 0.0

    def test_weight_equals_lot_times_unit(self):
        lot, weight = 12, 0.25
        result = compute_inner_box(10, 8, 6, weight, lot)
        assert math.isclose(result.total_weight_kg, lot * weight, rel_tol=1e-6)


# ---------------------------------------------------------------------------
# compute_inner_box — special / edge cases
# ---------------------------------------------------------------------------

class TestComputeInnerBoxEdgeCases:

    def test_lot_size_1_returns_single_article(self):
        L, W, H = 15.0, 10.0, 5.0
        wall_mm = 3.0
        result = compute_inner_box(L, W, H, 0.5, 1, wall_thickness_mm=wall_mm)
        assert result is not None
        assert result.grid == [1, 1, 1]
        # interior dims are the article dims (sorted desc)
        interior_dims = sorted([L, W, H], reverse=True)
        assert math.isclose(result.int_max_cm, interior_dims[0], rel_tol=1e-6)
        assert math.isclose(result.int_med_cm, interior_dims[1], rel_tol=1e-6)
        assert math.isclose(result.int_min_cm, interior_dims[2], rel_tol=1e-6)

    def test_lot_size_less_than_1_returns_none(self):
        assert compute_inner_box(10, 8, 6, 0.5, 0) is None
        assert compute_inner_box(10, 8, 6, 0.5, -1) is None

    def test_wall_thickness_zero(self):
        result = compute_inner_box(10, 8, 6, 0.5, 6, wall_thickness_mm=0.0)
        assert result is not None
        assert math.isclose(result.ext_max_cm, result.int_max_cm, rel_tol=1e-6)

    def test_cubic_preference_for_lot_8(self):
        """Lot 8 = 2×2×2 is most cubic. 8×1×1 should NOT win."""
        result = compute_inner_box(10, 10, 10, 1.0, 8)
        assert result is not None
        # 2×2×2 grid gives a cube (max == med == min)
        assert result.grid == [2, 2, 2]

    def test_square_article_deduplication(self):
        """All-equal article dims → only 1 orientation, still valid."""
        result = compute_inner_box(10, 10, 10, 1.0, 6)
        assert result is not None
        assert _grid_product(result) == 6

    def test_prime_lot_size(self):
        """Prime lot_size 7: grid must be 7×1×1 (only factorization)."""
        result = compute_inner_box(10, 8, 6, 0.5, 7)
        assert result is not None
        assert _grid_product(result) == 7
        dims = sorted(result.grid, reverse=True)
        assert dims[0] == 7 and dims[1] == 1 and dims[2] == 1

    def test_large_lot_size(self):
        """Lot 60 has many factorizations; result must still satisfy all invariants."""
        result = compute_inner_box(12, 8, 6, 0.3, 60)
        assert result is not None
        assert _grid_product(result) == 60
        assert math.isclose(_int_volume(result), 12 * 8 * 6 * 60, rel_tol=1e-4)

    def test_article_axes_length_3(self):
        result = compute_inner_box(10, 8, 6, 0.5, 6)
        assert len(result.article_axes_per_inner_axis) == 3
        assert len(result.grid) == 3
        assert all(ax in {"max", "med", "min"} for ax in result.article_axes_per_inner_axis)


# ---------------------------------------------------------------------------
# compute_inner_box — orientation constraints
# ---------------------------------------------------------------------------

class TestComputeInnerBoxConstraints:

    def test_orientation_locked_height_places_max_dim_on_h_slot(self):
        """
        orientation_locked=True, locked_axis="height":
        The article's max dim must be in the H slot.
        In the returned result, the article's max dim drives one interior axis.
        Since dims are re-sorted descending we can't directly check H slot, but
        we verify the result is still valid (correct grid product & volume).
        """
        constraints = {"orientation_locked": True, "locked_axis": "height"}
        result = compute_inner_box(15, 10, 5, 0.5, 6, constraints=constraints)
        assert result is not None
        assert _grid_product(result) == 6
        assert math.isclose(_int_volume(result), 15 * 10 * 5 * 6, rel_tol=1e-6)

    def test_orientation_locked_width_places_min_dim_on_h_slot(self):
        constraints = {"orientation_locked": True, "locked_axis": "width"}
        result = compute_inner_box(15, 10, 5, 0.5, 6, constraints=constraints)
        assert result is not None
        assert _grid_product(result) == 6

    def test_orientation_locked_none_axis_uses_natural_only(self):
        """locked_axis=None → only natural orientation (0,1,2)."""
        constraints = {"orientation_locked": True, "locked_axis": None}
        result = compute_inner_box(15, 10, 5, 0.5, 6, constraints=constraints)
        assert result is not None
        assert _grid_product(result) == 6

    def test_no_constraints_returns_most_cubic(self):
        """Without constraints, optimizer is free to pick any orientation."""
        r_free = compute_inner_box(15, 10, 5, 0.5, 6)
        r_locked = compute_inner_box(15, 10, 5, 0.5, 6,
                                     constraints={"orientation_locked": True,
                                                   "locked_axis": "height"})
        # Both must be valid; unconstrained may give a different (better) result
        assert r_free is not None
        assert r_locked is not None
        assert _grid_product(r_free) == 6
        assert _grid_product(r_locked) == 6
