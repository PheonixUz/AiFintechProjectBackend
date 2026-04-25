"""
GET /api/v1/data/* endpointlariga integration testlar.

DataRepository mocked — DB talab qilinmaydi.
HTTP qatlami, validatsiya va response sxemalari tekshiriladi.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from factories import (
    make_benchmark,
    make_business,
    make_customer_segment,
    make_market_estimate,
    make_mcc_category,
    make_poi,
    make_population_zone,
)

PATCH_TARGET = "app.api.routes.data.DataRepository"


def _patch_repo(mock_repo_instance):
    """DataRepository classini mock instance bilan almashtiradi."""
    p = patch(PATCH_TARGET)
    MockClass = p.start()
    MockClass.return_value = mock_repo_instance
    return p


# ── GET /api/v1/data/niches ────────────────────────────────────────────────────


class TestGetNiches:
    def test_returns_200_with_list(self, client):
        mock_repo = AsyncMock()
        mock_repo.get_mcc_categories.return_value = [make_mcc_category()]
        p = _patch_repo(mock_repo)
        try:
            response = client.get("/api/v1/data/niches")
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 1
        finally:
            p.stop()

    def test_response_has_required_fields(self, client):
        mock_repo = AsyncMock()
        mock_repo.get_mcc_categories.return_value = [make_mcc_category()]
        p = _patch_repo(mock_repo)
        try:
            response = client.get("/api/v1/data/niches")
            item = response.json()[0]
            assert "mcc_code" in item
            assert "niche_name_uz" in item
            assert "parent_category" in item
            assert "is_active" in item
        finally:
            p.stop()

    def test_empty_db_returns_empty_list(self, client):
        mock_repo = AsyncMock()
        mock_repo.get_mcc_categories.return_value = []
        p = _patch_repo(mock_repo)
        try:
            response = client.get("/api/v1/data/niches")
            assert response.status_code == 200
            assert response.json() == []
        finally:
            p.stop()

    def test_active_only_false_calls_correct_method(self, client):
        mock_repo = AsyncMock()
        mock_repo.get_mcc_categories.return_value = []
        p = _patch_repo(mock_repo)
        try:
            client.get("/api/v1/data/niches?active_only=false")
            mock_repo.get_mcc_categories.assert_called_once_with(active_only=False)
        finally:
            p.stop()

    def test_parent_category_filter_calls_correct_method(self, client):
        mock_repo = AsyncMock()
        mock_repo.get_mcc_by_parent.return_value = [make_mcc_category()]
        p = _patch_repo(mock_repo)
        try:
            response = client.get("/api/v1/data/niches?parent_category=Oziq-ovqat")
            assert response.status_code == 200
            mock_repo.get_mcc_by_parent.assert_called_once_with("Oziq-ovqat")
        finally:
            p.stop()

    def test_multiple_categories_returned(self, client):
        cats = [make_mcc_category(id=i, mcc_code=f"58{i:02d}") for i in range(5)]
        mock_repo = AsyncMock()
        mock_repo.get_mcc_categories.return_value = cats
        p = _patch_repo(mock_repo)
        try:
            response = client.get("/api/v1/data/niches")
            assert len(response.json()) == 5
        finally:
            p.stop()


# ── GET /api/v1/data/benchmarks ───────────────────────────────────────────────


class TestGetBenchmarks:
    def test_returns_200_with_list(self, client):
        mock_repo = AsyncMock()
        mock_repo.get_benchmarks.return_value = [make_benchmark()]
        p = _patch_repo(mock_repo)
        try:
            response = client.get("/api/v1/data/benchmarks")
            assert response.status_code == 200
            assert len(response.json()) == 1
        finally:
            p.stop()

    def test_response_has_required_fields(self, client):
        mock_repo = AsyncMock()
        mock_repo.get_benchmarks.return_value = [make_benchmark()]
        p = _patch_repo(mock_repo)
        try:
            response = client.get("/api/v1/data/benchmarks")
            item = response.json()[0]
            for field in [
                "mcc_code",
                "niche",
                "city",
                "avg_monthly_revenue_uzs",
                "gross_margin_pct",
                "annual_growth_rate_pct",
                "data_year",
            ]:
                assert field in item
        finally:
            p.stop()

    def test_default_city_is_toshkent(self, client):
        mock_repo = AsyncMock()
        mock_repo.get_benchmarks.return_value = []
        p = _patch_repo(mock_repo)
        try:
            client.get("/api/v1/data/benchmarks")
            mock_repo.get_benchmarks.assert_called_once_with(
                city="Toshkent", mcc_code=None, niche=None
            )
        finally:
            p.stop()

    def test_mcc_code_filter_passed_to_repo(self, client):
        mock_repo = AsyncMock()
        mock_repo.get_benchmarks.return_value = []
        p = _patch_repo(mock_repo)
        try:
            client.get("/api/v1/data/benchmarks?mcc_code=5812")
            mock_repo.get_benchmarks.assert_called_once_with(
                city="Toshkent", mcc_code="5812", niche=None
            )
        finally:
            p.stop()

    def test_niche_filter_passed_to_repo(self, client):
        mock_repo = AsyncMock()
        mock_repo.get_benchmarks.return_value = []
        p = _patch_repo(mock_repo)
        try:
            client.get("/api/v1/data/benchmarks?niche=restoran")
            mock_repo.get_benchmarks.assert_called_once_with(
                city="Toshkent", mcc_code=None, niche="restoran"
            )
        finally:
            p.stop()

    def test_empty_returns_empty_list(self, client):
        mock_repo = AsyncMock()
        mock_repo.get_benchmarks.return_value = []
        p = _patch_repo(mock_repo)
        try:
            response = client.get("/api/v1/data/benchmarks")
            assert response.json() == []
        finally:
            p.stop()


# ── GET /api/v1/data/competitors ──────────────────────────────────────────────


class TestGetCompetitors:
    def test_returns_200(self, client):
        mock_repo = AsyncMock()
        mock_repo.get_competitors.return_value = [
            {"business": make_business(), "distance_m": 250.0}
        ]
        p = _patch_repo(mock_repo)
        try:
            response = client.get(
                "/api/v1/data/competitors?niche=restoran&lat=41.3&lon=69.3"
            )
            assert response.status_code == 200
        finally:
            p.stop()

    def test_response_structure(self, client):
        mock_repo = AsyncMock()
        mock_repo.get_competitors.return_value = [
            {"business": make_business(), "distance_m": 250.0}
        ]
        p = _patch_repo(mock_repo)
        try:
            response = client.get(
                "/api/v1/data/competitors?niche=restoran&lat=41.3&lon=69.3"
            )
            data = response.json()
            assert "niche" in data
            assert "total_count" in data
            assert "competitors" in data
            assert data["total_count"] == 1
        finally:
            p.stop()

    def test_competitor_has_distance_m(self, client):
        mock_repo = AsyncMock()
        mock_repo.get_competitors.return_value = [
            {"business": make_business(), "distance_m": 350.7}
        ]
        p = _patch_repo(mock_repo)
        try:
            response = client.get(
                "/api/v1/data/competitors?niche=restoran&lat=41.3&lon=69.3"
            )
            competitor = response.json()["competitors"][0]
            assert competitor["distance_m"] == pytest.approx(350.7, abs=0.01)
        finally:
            p.stop()

    def test_empty_result_returns_zero_count(self, client):
        mock_repo = AsyncMock()
        mock_repo.get_competitors.return_value = []
        p = _patch_repo(mock_repo)
        try:
            response = client.get(
                "/api/v1/data/competitors?niche=restoran&lat=41.3&lon=69.3"
            )
            assert response.json()["total_count"] == 0
            assert response.json()["competitors"] == []
        finally:
            p.stop()

    def test_missing_niche_returns_422(self, client):
        response = client.get("/api/v1/data/competitors?lat=41.3&lon=69.3")
        assert response.status_code == 422

    def test_missing_lat_returns_422(self, client):
        response = client.get("/api/v1/data/competitors?niche=restoran&lon=69.3")
        assert response.status_code == 422

    def test_missing_lon_returns_422(self, client):
        response = client.get("/api/v1/data/competitors?niche=restoran&lat=41.3")
        assert response.status_code == 422

    def test_invalid_lat_range_returns_422(self, client):
        response = client.get(
            "/api/v1/data/competitors?niche=restoran&lat=200&lon=69.3"
        )
        assert response.status_code == 422

    def test_radius_too_small_returns_422(self, client):
        response = client.get(
            "/api/v1/data/competitors?niche=restoran&lat=41.3&lon=69.3&radius_m=50"
        )
        assert response.status_code == 422

    def test_default_radius_is_1000(self, client):
        mock_repo = AsyncMock()
        mock_repo.get_competitors.return_value = []
        p = _patch_repo(mock_repo)
        try:
            client.get("/api/v1/data/competitors?niche=restoran&lat=41.3&lon=69.3")
            _, kwargs = mock_repo.get_competitors.call_args
            assert kwargs.get("radius_m", 1000) == 1000
        finally:
            p.stop()

    def test_custom_radius_passed_to_repo(self, client):
        mock_repo = AsyncMock()
        mock_repo.get_competitors.return_value = []
        p = _patch_repo(mock_repo)
        try:
            client.get(
                "/api/v1/data/competitors?niche=restoran&lat=41.3&lon=69.3&radius_m=2000"
            )
            call_kwargs = mock_repo.get_competitors.call_args
            assert (
                2000.0 in call_kwargs.args
                or call_kwargs.kwargs.get("radius_m") == 2000.0
            )
        finally:
            p.stop()


# ── GET /api/v1/data/transactions ─────────────────────────────────────────────


class TestGetTransactions:
    def test_returns_200(self, client):
        mock_repo = AsyncMock()
        mock_repo.get_transaction_monthly_breakdown.return_value = [
            {"month": 1, "total_uzs": Decimal("100_000_000"), "transaction_count": 150}
        ]
        p = _patch_repo(mock_repo)
        try:
            response = client.get("/api/v1/data/transactions?mcc_code=5812")
            assert response.status_code == 200
        finally:
            p.stop()

    def test_response_structure(self, client):
        mock_repo = AsyncMock()
        mock_repo.get_transaction_monthly_breakdown.return_value = []
        p = _patch_repo(mock_repo)
        try:
            response = client.get("/api/v1/data/transactions?mcc_code=5812")
            data = response.json()
            assert "mcc_code" in data
            assert "city" in data
            assert "year" in data
            assert "annual_total_uzs" in data
            assert "monthly_breakdown" in data
            assert "months_with_data" in data
        finally:
            p.stop()

    def test_annual_total_is_sum_of_months(self, client):
        mock_repo = AsyncMock()
        mock_repo.get_transaction_monthly_breakdown.return_value = [
            {"month": m, "total_uzs": Decimal("100_000_000"), "transaction_count": 100}
            for m in range(1, 5)
        ]
        p = _patch_repo(mock_repo)
        try:
            response = client.get("/api/v1/data/transactions?mcc_code=5812")
            data = response.json()
            assert Decimal(data["annual_total_uzs"]) == Decimal("400_000_000")
            assert data["months_with_data"] == 4
        finally:
            p.stop()

    def test_empty_data_returns_zero_total(self, client):
        mock_repo = AsyncMock()
        mock_repo.get_transaction_monthly_breakdown.return_value = []
        p = _patch_repo(mock_repo)
        try:
            response = client.get("/api/v1/data/transactions?mcc_code=5812")
            data = response.json()
            assert Decimal(data["annual_total_uzs"]) == Decimal("0")
            assert data["months_with_data"] == 0
        finally:
            p.stop()

    def test_missing_mcc_code_returns_422(self, client):
        response = client.get("/api/v1/data/transactions")
        assert response.status_code == 422

    def test_mcc_code_too_short_returns_422(self, client):
        response = client.get("/api/v1/data/transactions?mcc_code=58")
        assert response.status_code == 422

    def test_mcc_code_too_long_returns_422(self, client):
        response = client.get("/api/v1/data/transactions?mcc_code=58120")
        assert response.status_code == 422

    def test_invalid_year_range_returns_422(self, client):
        response = client.get("/api/v1/data/transactions?mcc_code=5812&year=2019")
        assert response.status_code == 422

    def test_default_city_toshkent(self, client):
        mock_repo = AsyncMock()
        mock_repo.get_transaction_monthly_breakdown.return_value = []
        p = _patch_repo(mock_repo)
        try:
            response = client.get("/api/v1/data/transactions?mcc_code=5812")
            assert response.json()["city"] == "Toshkent"
        finally:
            p.stop()

    def test_custom_year_passed(self, client):
        mock_repo = AsyncMock()
        mock_repo.get_transaction_monthly_breakdown.return_value = []
        p = _patch_repo(mock_repo)
        try:
            response = client.get("/api/v1/data/transactions?mcc_code=5812&year=2024")
            assert response.json()["year"] == 2024
        finally:
            p.stop()


# ── GET /api/v1/data/population ───────────────────────────────────────────────


class TestGetPopulation:
    def test_returns_200(self, client):
        mock_repo = AsyncMock()
        mock_repo.get_population_zones.return_value = [make_population_zone()]
        p = _patch_repo(mock_repo)
        try:
            response = client.get("/api/v1/data/population?lat=41.3&lon=69.3")
            assert response.status_code == 200
        finally:
            p.stop()

    def test_response_structure(self, client):
        mock_repo = AsyncMock()
        mock_repo.get_population_zones.return_value = []
        p = _patch_repo(mock_repo)
        try:
            response = client.get("/api/v1/data/population?lat=41.3&lon=69.3")
            data = response.json()
            assert "lat" in data
            assert "lon" in data
            assert "radius_m" in data
            assert "zones_count" in data
            assert "total_population" in data
            assert "zones" in data
        finally:
            p.stop()

    def test_total_population_is_sum_of_zones(self, client):
        zones = [
            make_population_zone(id=1, total_population=10_000),
            make_population_zone(id=2, total_population=5_000),
        ]
        mock_repo = AsyncMock()
        mock_repo.get_population_zones.return_value = zones
        p = _patch_repo(mock_repo)
        try:
            response = client.get("/api/v1/data/population?lat=41.3&lon=69.3")
            data = response.json()
            assert data["total_population"] == 15_000
            assert data["zones_count"] == 2
        finally:
            p.stop()

    def test_missing_lat_returns_422(self, client):
        response = client.get("/api/v1/data/population?lon=69.3")
        assert response.status_code == 422

    def test_missing_lon_returns_422(self, client):
        response = client.get("/api/v1/data/population?lat=41.3")
        assert response.status_code == 422

    def test_radius_too_large_returns_422(self, client):
        response = client.get(
            "/api/v1/data/population?lat=41.3&lon=69.3&radius_m=50000"
        )
        assert response.status_code == 422

    def test_zone_fields_present(self, client):
        mock_repo = AsyncMock()
        mock_repo.get_population_zones.return_value = [make_population_zone()]
        p = _patch_repo(mock_repo)
        try:
            response = client.get("/api/v1/data/population?lat=41.3&lon=69.3")
            zone = response.json()["zones"][0]
            for field in [
                "zone_name",
                "district",
                "total_population",
                "avg_monthly_income_uzs",
                "data_year",
            ]:
                assert field in zone
        finally:
            p.stop()


# ── GET /api/v1/data/poi ──────────────────────────────────────────────────────


class TestGetPOI:
    def test_returns_200(self, client):
        mock_repo = AsyncMock()
        mock_repo.get_pois.return_value = [{"poi": make_poi(), "distance_m": 100.0}]
        p = _patch_repo(mock_repo)
        try:
            response = client.get("/api/v1/data/poi?lat=41.3&lon=69.3")
            assert response.status_code == 200
        finally:
            p.stop()

    def test_response_structure(self, client):
        mock_repo = AsyncMock()
        mock_repo.get_pois.return_value = []
        p = _patch_repo(mock_repo)
        try:
            response = client.get("/api/v1/data/poi?lat=41.3&lon=69.3")
            data = response.json()
            assert "lat" in data
            assert "lon" in data
            assert "radius_m" in data
            assert "poi_type" in data
            assert "total_count" in data
            assert "pois" in data
        finally:
            p.stop()

    def test_poi_has_distance_m(self, client):
        mock_repo = AsyncMock()
        mock_repo.get_pois.return_value = [{"poi": make_poi(), "distance_m": 123.4}]
        p = _patch_repo(mock_repo)
        try:
            response = client.get("/api/v1/data/poi?lat=41.3&lon=69.3")
            poi = response.json()["pois"][0]
            assert poi["distance_m"] == pytest.approx(123.4, abs=0.01)
        finally:
            p.stop()

    def test_poi_type_filter_passed_to_repo(self, client):
        mock_repo = AsyncMock()
        mock_repo.get_pois.return_value = []
        p = _patch_repo(mock_repo)
        try:
            client.get("/api/v1/data/poi?lat=41.3&lon=69.3&poi_type=market")
            call_args = mock_repo.get_pois.call_args
            assert call_args.kwargs.get("poi_type") == "market"
        finally:
            p.stop()

    def test_poi_type_none_by_default(self, client):
        mock_repo = AsyncMock()
        mock_repo.get_pois.return_value = []
        p = _patch_repo(mock_repo)
        try:
            response = client.get("/api/v1/data/poi?lat=41.3&lon=69.3")
            assert response.json()["poi_type"] is None
        finally:
            p.stop()

    def test_empty_result_zero_count(self, client):
        mock_repo = AsyncMock()
        mock_repo.get_pois.return_value = []
        p = _patch_repo(mock_repo)
        try:
            response = client.get("/api/v1/data/poi?lat=41.3&lon=69.3")
            assert response.json()["total_count"] == 0
        finally:
            p.stop()

    def test_missing_lat_returns_422(self, client):
        response = client.get("/api/v1/data/poi?lon=69.3")
        assert response.status_code == 422

    def test_radius_too_large_returns_422(self, client):
        response = client.get("/api/v1/data/poi?lat=41.3&lon=69.3&radius_m=10000")
        assert response.status_code == 422

    def test_poi_fields_present(self, client):
        mock_repo = AsyncMock()
        mock_repo.get_pois.return_value = [{"poi": make_poi(), "distance_m": 50.0}]
        p = _patch_repo(mock_repo)
        try:
            response = client.get("/api/v1/data/poi?lat=41.3&lon=69.3")
            poi = response.json()["pois"][0]
            for field in ["id", "name", "poi_type", "lat", "lon", "distance_m"]:
                assert field in poi
        finally:
            p.stop()


# ── GET /api/v1/data/customer-segments ────────────────────────────────────────


class TestGetCustomerSegments:
    def test_returns_200(self, client):
        mock_repo = AsyncMock()
        mock_repo.get_customer_segments.return_value = [make_customer_segment()]
        p = _patch_repo(mock_repo)
        try:
            response = client.get("/api/v1/data/customer-segments?lat=41.3&lon=69.3")
            assert response.status_code == 200
        finally:
            p.stop()

    def test_response_structure(self, client):
        mock_repo = AsyncMock()
        mock_repo.get_customer_segments.return_value = []
        p = _patch_repo(mock_repo)
        try:
            response = client.get("/api/v1/data/customer-segments?lat=41.3&lon=69.3")
            data = response.json()
            assert "segments_count" in data
            assert "total_customers_est" in data
            assert "segments" in data
        finally:
            p.stop()

    def test_total_customers_is_sum(self, client):
        segs = [
            make_customer_segment(id=1, estimated_count=3000),
            make_customer_segment(id=2, estimated_count=2000),
        ]
        mock_repo = AsyncMock()
        mock_repo.get_customer_segments.return_value = segs
        p = _patch_repo(mock_repo)
        try:
            response = client.get("/api/v1/data/customer-segments?lat=41.3&lon=69.3")
            data = response.json()
            assert data["total_customers_est"] == 5000
            assert data["segments_count"] == 2
        finally:
            p.stop()

    def test_segment_fields_present(self, client):
        mock_repo = AsyncMock()
        mock_repo.get_customer_segments.return_value = [make_customer_segment()]
        p = _patch_repo(mock_repo)
        try:
            response = client.get("/api/v1/data/customer-segments?lat=41.3&lon=69.3")
            seg = response.json()["segments"][0]
            for field in [
                "segment_name",
                "district",
                "avg_monthly_spending_uzs",
                "purchase_frequency_monthly",
                "estimated_count",
            ]:
                assert field in seg
        finally:
            p.stop()

    def test_missing_lat_returns_422(self, client):
        response = client.get("/api/v1/data/customer-segments?lon=69.3")
        assert response.status_code == 422

    def test_radius_too_large_returns_422(self, client):
        response = client.get(
            "/api/v1/data/customer-segments?lat=41.3&lon=69.3&radius_m=50000"
        )
        assert response.status_code == 422

    def test_city_filter_passed_to_repo(self, client):
        mock_repo = AsyncMock()
        mock_repo.get_customer_segments.return_value = []
        p = _patch_repo(mock_repo)
        try:
            client.get(
                "/api/v1/data/customer-segments?lat=41.3&lon=69.3&city=Samarqand"
            )
            call_args = mock_repo.get_customer_segments.call_args
            assert call_args.kwargs.get("city") == "Samarqand"
        finally:
            p.stop()


# ── GET /api/v1/data/market-estimates ─────────────────────────────────────────


class TestGetMarketEstimates:
    def test_returns_200(self, client):
        mock_repo = AsyncMock()
        mock_repo.get_market_estimates.return_value = [make_market_estimate()]
        p = _patch_repo(mock_repo)
        try:
            response = client.get("/api/v1/data/market-estimates?niche=restoran")
            assert response.status_code == 200
        finally:
            p.stop()

    def test_response_is_list(self, client):
        mock_repo = AsyncMock()
        mock_repo.get_market_estimates.return_value = [make_market_estimate()]
        p = _patch_repo(mock_repo)
        try:
            response = client.get("/api/v1/data/market-estimates?niche=restoran")
            assert isinstance(response.json(), list)
        finally:
            p.stop()

    def test_estimate_fields_present(self, client):
        mock_repo = AsyncMock()
        mock_repo.get_market_estimates.return_value = [make_market_estimate()]
        p = _patch_repo(mock_repo)
        try:
            response = client.get("/api/v1/data/market-estimates?niche=restoran")
            est = response.json()[0]
            for field in [
                "niche",
                "mcc_code",
                "city",
                "tam_uzs",
                "sam_uzs",
                "som_uzs",
                "competitor_count",
                "confidence_score",
                "calculation_date",
            ]:
                assert field in est
        finally:
            p.stop()

    def test_empty_returns_empty_list(self, client):
        mock_repo = AsyncMock()
        mock_repo.get_market_estimates.return_value = []
        p = _patch_repo(mock_repo)
        try:
            response = client.get("/api/v1/data/market-estimates?niche=restoran")
            assert response.json() == []
        finally:
            p.stop()

    def test_missing_niche_returns_422(self, client):
        response = client.get("/api/v1/data/market-estimates")
        assert response.status_code == 422

    def test_limit_param_passed_to_repo(self, client):
        mock_repo = AsyncMock()
        mock_repo.get_market_estimates.return_value = []
        p = _patch_repo(mock_repo)
        try:
            client.get("/api/v1/data/market-estimates?niche=restoran&limit=5")
            call_args = mock_repo.get_market_estimates.call_args
            assert call_args.kwargs.get("limit") == 5
        finally:
            p.stop()

    def test_limit_too_large_returns_422(self, client):
        response = client.get("/api/v1/data/market-estimates?niche=restoran&limit=100")
        assert response.status_code == 422

    def test_city_filter_passed_to_repo(self, client):
        mock_repo = AsyncMock()
        mock_repo.get_market_estimates.return_value = []
        p = _patch_repo(mock_repo)
        try:
            client.get("/api/v1/data/market-estimates?niche=restoran&city=Samarqand")
            call_args = mock_repo.get_market_estimates.call_args
            assert call_args.kwargs.get("city") == "Samarqand"
        finally:
            p.stop()


# ── GET /api/v1/data/market-estimates/by-location ─────────────────────────────


class TestGetMarketEstimateByLocation:
    def test_returns_200_when_found(self, client):
        mock_repo = AsyncMock()
        mock_repo.get_market_estimate_by_location.return_value = make_market_estimate()
        p = _patch_repo(mock_repo)
        try:
            response = client.get(
                "/api/v1/data/market-estimates/by-location"
                "?niche=restoran&lat=41.3&lon=69.3"
            )
            assert response.status_code == 200
        finally:
            p.stop()

    def test_returns_null_when_not_found(self, client):
        mock_repo = AsyncMock()
        mock_repo.get_market_estimate_by_location.return_value = None
        p = _patch_repo(mock_repo)
        try:
            response = client.get(
                "/api/v1/data/market-estimates/by-location"
                "?niche=restoran&lat=41.3&lon=69.3"
            )
            assert response.status_code == 200
            assert response.json() is None
        finally:
            p.stop()

    def test_estimate_fields_when_found(self, client):
        mock_repo = AsyncMock()
        mock_repo.get_market_estimate_by_location.return_value = make_market_estimate()
        p = _patch_repo(mock_repo)
        try:
            response = client.get(
                "/api/v1/data/market-estimates/by-location"
                "?niche=restoran&lat=41.3&lon=69.3"
            )
            data = response.json()
            assert data["niche"] == "restoran"
            assert "tam_uzs" in data
            assert "sam_uzs" in data
            assert "som_uzs" in data
        finally:
            p.stop()

    def test_missing_niche_returns_422(self, client):
        response = client.get(
            "/api/v1/data/market-estimates/by-location?lat=41.3&lon=69.3"
        )
        assert response.status_code == 422

    def test_missing_lat_returns_422(self, client):
        response = client.get(
            "/api/v1/data/market-estimates/by-location?niche=restoran&lon=69.3"
        )
        assert response.status_code == 422

    def test_calculation_date_passed_to_repo(self, client):
        mock_repo = AsyncMock()
        mock_repo.get_market_estimate_by_location.return_value = None
        p = _patch_repo(mock_repo)
        try:
            client.get(
                "/api/v1/data/market-estimates/by-location"
                "?niche=restoran&lat=41.3&lon=69.3&calculation_date=2025-04-25"
            )
            call_args = mock_repo.get_market_estimate_by_location.call_args
            assert call_args.kwargs.get("calculation_date") == date(2025, 4, 25)
        finally:
            p.stop()

    def test_invalid_date_format_returns_422(self, client):
        response = client.get(
            "/api/v1/data/market-estimates/by-location"
            "?niche=restoran&lat=41.3&lon=69.3&calculation_date=25-04-2025"
        )
        assert response.status_code == 422

    def test_invalid_lat_range_returns_422(self, client):
        response = client.get(
            "/api/v1/data/market-estimates/by-location?niche=restoran&lat=200&lon=69.3"
        )
        assert response.status_code == 422
