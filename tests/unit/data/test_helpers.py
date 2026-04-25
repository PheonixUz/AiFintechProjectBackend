"""_bounding_box va _haversine_m sof funksiyalariga unit testlar."""

import math

import pytest

from app.db.repositories.data_repo import _bounding_box, _haversine_m


class TestBoundingBox:
    def test_returns_four_values(self):
        result = _bounding_box(41.3, 69.3, 1000)
        assert len(result) == 4

    def test_min_lat_less_than_max_lat(self):
        min_lat, max_lat, _, _ = _bounding_box(41.3, 69.3, 1000)
        assert min_lat < max_lat

    def test_min_lon_less_than_max_lon(self):
        _, _, min_lon, max_lon = _bounding_box(41.3, 69.3, 1000)
        assert min_lon < max_lon

    def test_center_is_midpoint(self):
        lat, lon = 41.3, 69.3
        min_lat, max_lat, min_lon, max_lon = _bounding_box(lat, lon, 1000)
        assert abs((min_lat + max_lat) / 2 - lat) < 1e-10
        assert abs((min_lon + max_lon) / 2 - lon) < 1e-10

    def test_larger_radius_gives_wider_box(self):
        _, _, min_lon_500, max_lon_500 = _bounding_box(41.3, 69.3, 500)
        _, _, min_lon_2000, max_lon_2000 = _bounding_box(41.3, 69.3, 2000)
        assert (max_lon_2000 - min_lon_2000) > (max_lon_500 - min_lon_500)

    def test_lat_delta_formula(self):
        min_lat, max_lat, _, _ = _bounding_box(0.0, 0.0, 1000)
        expected_delta = 1000 / 111_000
        actual_delta = (max_lat - min_lat) / 2
        assert abs(actual_delta - expected_delta) < 1e-10

    def test_equator_lat_lon_delta_equal(self):
        # ekvatorida cos(0)=1, shuning uchun lat_delta == lon_delta
        min_lat, max_lat, min_lon, max_lon = _bounding_box(0.0, 0.0, 1000)
        lat_delta = (max_lat - min_lat) / 2
        lon_delta = (max_lon - min_lon) / 2
        assert abs(lat_delta - lon_delta) < 1e-10

    def test_high_latitude_wider_lon_delta(self):
        # Yuqori kenglikda (masalan 60°) lon_delta kattaroq bo'ladi
        _, _, min_lon_eq, max_lon_eq = _bounding_box(0.0, 0.0, 1000)
        _, _, min_lon_60, max_lon_60 = _bounding_box(60.0, 0.0, 1000)
        lon_span_eq = max_lon_eq - min_lon_eq
        lon_span_60 = max_lon_60 - min_lon_60
        assert lon_span_60 > lon_span_eq

    def test_zero_radius_gives_point_box(self):
        min_lat, max_lat, min_lon, max_lon = _bounding_box(41.3, 69.3, 0)
        assert min_lat == max_lat
        assert min_lon == max_lon

    def test_negative_lat_handled(self):
        result = _bounding_box(-33.9, 151.2, 1000)
        assert len(result) == 4
        min_lat, max_lat, min_lon, max_lon = result
        assert min_lat < max_lat


class TestHaversine:
    def test_same_point_zero_distance(self):
        assert _haversine_m(41.3, 69.3, 41.3, 69.3) == 0.0

    def test_symmetry(self):
        d1 = _haversine_m(41.3, 69.3, 41.4, 69.4)
        d2 = _haversine_m(41.4, 69.4, 41.3, 69.3)
        assert abs(d1 - d2) < 1e-6

    def test_positive_distance(self):
        assert _haversine_m(41.0, 69.0, 42.0, 70.0) > 0

    def test_approximate_1_degree_lat(self):
        # 1 daraja kenglik ≈ 111 km
        dist = _haversine_m(0.0, 0.0, 1.0, 0.0)
        assert 110_000 < dist < 112_000

    def test_approximate_1_degree_lon_at_equator(self):
        # Ekvatorida 1 daraja uzunlik ≈ 111 km
        dist = _haversine_m(0.0, 0.0, 0.0, 1.0)
        assert 110_000 < dist < 112_000

    def test_100m_approximately(self):
        # 0.001 daraja kenglik ≈ 111 m
        dist = _haversine_m(41.3, 69.3, 41.301, 69.3)
        assert 100 < dist < 130

    def test_tashkent_samarkand_distance(self):
        # Toshkent → Samarqand taxminan 267 km
        dist = _haversine_m(41.299, 69.240, 39.627, 66.976)
        assert 260_000 < dist < 280_000

    def test_result_is_in_meters(self):
        # 1 daraja kenglik metrda ~111_000 bo'lishi kerak
        dist = _haversine_m(0.0, 0.0, 1.0, 0.0)
        assert dist > 1000  # metrlarda, km emas

    def test_antipodal_points_max_distance(self):
        # Yer sharida eng katta masofa ≈ 20_015 km
        dist = _haversine_m(0.0, 0.0, 0.0, 180.0)
        assert abs(dist - 20_015_087) < 1000
