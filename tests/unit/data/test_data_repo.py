"""DataRepository metodlariga unit testlar (mocked AsyncSession)."""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest
from factories import (
    make_async_session,
    make_benchmark,
    make_business,
    make_customer_segment,
    make_market_estimate,
    make_mcc_category,
    make_poi,
    make_population_zone,
)

from app.db.repositories.data_repo import DataRepository

# ── MCC Kategoriyalar ──────────────────────────────────────────────────────────


class TestGetMCCCategories:
    @pytest.mark.asyncio
    async def test_returns_all_categories(self):
        cats = [make_mcc_category(id=i, mcc_code=f"58{i:02d}") for i in range(3)]
        session = make_async_session(scalars_result=cats)
        result = await DataRepository(session).get_mcc_categories()
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_empty_db_returns_empty_list(self):
        session = make_async_session(scalars_result=[])
        result = await DataRepository(session).get_mcc_categories()
        assert result == []

    @pytest.mark.asyncio
    async def test_executes_exactly_one_query(self):
        session = make_async_session(scalars_result=[])
        await DataRepository(session).get_mcc_categories()
        session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_inactive_filter_also_executes_once(self):
        session = make_async_session(scalars_result=[])
        await DataRepository(session).get_mcc_categories(active_only=False)
        session.execute.assert_called_once()


class TestGetMCCByParent:
    @pytest.mark.asyncio
    async def test_returns_matching_categories(self):
        cat = make_mcc_category(parent_category="Oziq-ovqat")
        session = make_async_session(scalars_result=[cat])
        result = await DataRepository(session).get_mcc_by_parent("Oziq-ovqat")
        assert result == [cat]

    @pytest.mark.asyncio
    async def test_empty_when_no_match(self):
        session = make_async_session(scalars_result=[])
        result = await DataRepository(session).get_mcc_by_parent("Mavjud_emas")
        assert result == []


# ── Benchmarklar ───────────────────────────────────────────────────────────────


class TestGetBenchmarks:
    @pytest.mark.asyncio
    async def test_returns_benchmarks_for_city(self):
        bench = make_benchmark()
        session = make_async_session(scalars_result=[bench])
        result = await DataRepository(session).get_benchmarks(city="Toshkent")
        assert result == [bench]

    @pytest.mark.asyncio
    async def test_returns_multiple_benchmarks(self):
        benches = [make_benchmark(id=i, niche=f"nisha_{i}") for i in range(5)]
        session = make_async_session(scalars_result=benches)
        result = await DataRepository(session).get_benchmarks(city="Toshkent")
        assert len(result) == 5

    @pytest.mark.asyncio
    async def test_empty_when_city_not_found(self):
        session = make_async_session(scalars_result=[])
        result = await DataRepository(session).get_benchmarks(city="Noma_lum_shahar")
        assert result == []

    @pytest.mark.asyncio
    async def test_mcc_filter_executes_query(self):
        session = make_async_session(scalars_result=[])
        await DataRepository(session).get_benchmarks(city="Toshkent", mcc_code="5812")
        session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_mcc_filter_only_executes_query(self):
        session = make_async_session(scalars_result=[])
        await DataRepository(session).get_benchmarks(city="Toshkent", mcc_code="5812")
        session.execute.assert_called_once()


# ── Raqobatchilar ──────────────────────────────────────────────────────────────


class TestGetCompetitors:
    @pytest.mark.asyncio
    async def test_competitor_at_center_included(self):
        b = make_business(lat=41.3, lon=69.3)
        session = make_async_session(scalars_result=[b])
        results = await DataRepository(session).get_competitors(
            "restoran", 41.3, 69.3, 1000
        )
        assert len(results) == 1
        assert results[0]["distance_m"] == pytest.approx(0.0, abs=0.1)

    @pytest.mark.asyncio
    async def test_competitor_outside_radius_excluded(self):
        # ~14 km uzoqlikda
        b = make_business(lat=41.43, lon=69.3)
        session = make_async_session(scalars_result=[b])
        results = await DataRepository(session).get_competitors(
            "restoran", 41.3, 69.3, 1000
        )
        assert results == []

    @pytest.mark.asyncio
    async def test_results_sorted_by_distance_ascending(self):
        near = make_business(id=1, lat=41.301, lon=69.3)  # ~111 m
        far = make_business(id=2, lat=41.307, lon=69.3)  # ~777 m
        session = make_async_session(scalars_result=[far, near])
        results = await DataRepository(session).get_competitors(
            "restoran", 41.3, 69.3, 1000
        )
        assert len(results) == 2
        assert results[0]["business"].id == 1
        assert results[0]["distance_m"] < results[1]["distance_m"]

    @pytest.mark.asyncio
    async def test_multiple_within_radius_all_returned(self):
        businesses = [
            make_business(id=i, lat=41.3 + i * 0.001, lon=69.3) for i in range(5)
        ]
        session = make_async_session(scalars_result=businesses)
        results = await DataRepository(session).get_competitors(
            "restoran", 41.3, 69.3, 1000
        )
        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_empty_db_returns_empty_list(self):
        session = make_async_session(scalars_result=[])
        results = await DataRepository(session).get_competitors(
            "restoran", 41.3, 69.3, 1000
        )
        assert results == []

    @pytest.mark.asyncio
    async def test_result_contains_business_and_distance(self):
        b = make_business(lat=41.3, lon=69.3)
        session = make_async_session(scalars_result=[b])
        results = await DataRepository(session).get_competitors(
            "restoran", 41.3, 69.3, 1000
        )
        assert "business" in results[0]
        assert "distance_m" in results[0]


# ── Tranzaksiya statistikasi ───────────────────────────────────────────────────


class TestGetTransactionMonthlyBreakdown:
    @pytest.mark.asyncio
    async def test_returns_12_months_when_full_year(self):
        rows = [
            SimpleNamespace(
                month=float(m), total_uzs=Decimal("100_000_000"), transaction_count=150
            )
            for m in range(1, 13)
        ]
        session = make_async_session(rows_result=rows)
        result = await DataRepository(session).get_transaction_monthly_breakdown(
            "5812", "Toshkent", 2025
        )
        assert len(result) == 12

    @pytest.mark.asyncio
    async def test_month_is_int(self):
        row = SimpleNamespace(
            month=1.0, total_uzs=Decimal("50_000_000"), transaction_count=100
        )
        session = make_async_session(rows_result=[row])
        result = await DataRepository(session).get_transaction_monthly_breakdown(
            "5812", "Toshkent", 2025
        )
        assert isinstance(result[0]["month"], int)
        assert result[0]["month"] == 1

    @pytest.mark.asyncio
    async def test_null_total_becomes_zero(self):
        row = SimpleNamespace(month=5.0, total_uzs=None, transaction_count=0)
        session = make_async_session(rows_result=[row])
        result = await DataRepository(session).get_transaction_monthly_breakdown(
            "5812", "Toshkent", 2025
        )
        assert result[0]["total_uzs"] == Decimal(0)

    @pytest.mark.asyncio
    async def test_empty_returns_empty_list(self):
        session = make_async_session(rows_result=[])
        result = await DataRepository(session).get_transaction_monthly_breakdown(
            "9999", "Andijon", 2020
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_result_has_correct_keys(self):
        row = SimpleNamespace(
            month=3.0, total_uzs=Decimal("30_000_000"), transaction_count=200
        )
        session = make_async_session(rows_result=[row])
        result = await DataRepository(session).get_transaction_monthly_breakdown(
            "5812", "Toshkent", 2025
        )
        assert set(result[0].keys()) == {"month", "total_uzs", "transaction_count"}


# ── Aholi zonalari ─────────────────────────────────────────────────────────────


class TestGetPopulationZones:
    @pytest.mark.asyncio
    async def test_zone_at_center_included(self):
        zone = make_population_zone(lat=41.3, lon=69.3)
        session = make_async_session(scalars_result=[zone])
        result = await DataRepository(session).get_population_zones(41.3, 69.3, 1000)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_zone_outside_radius_excluded(self):
        # ~12 km uzoqlikda
        zone = make_population_zone(lat=41.41, lon=69.3)
        session = make_async_session(scalars_result=[zone])
        result = await DataRepository(session).get_population_zones(41.3, 69.3, 1000)
        assert result == []

    @pytest.mark.asyncio
    async def test_multiple_zones_filtered_correctly(self):
        near = make_population_zone(id=1, lat=41.302, lon=69.3)  # ~222 m
        far = make_population_zone(id=2, lat=41.42, lon=69.3)  # ~13.4 km
        session = make_async_session(scalars_result=[near, far])
        result = await DataRepository(session).get_population_zones(41.3, 69.3, 1000)
        assert len(result) == 1
        assert result[0].id == 1

    @pytest.mark.asyncio
    async def test_empty_db_returns_empty(self):
        session = make_async_session(scalars_result=[])
        result = await DataRepository(session).get_population_zones(41.3, 69.3, 1000)
        assert result == []

    @pytest.mark.asyncio
    async def test_large_radius_includes_more_zones(self):
        zones = [
            make_population_zone(id=i, lat=41.3 + i * 0.01, lon=69.3) for i in range(5)
        ]
        session = make_async_session(scalars_result=zones)
        result_small = await DataRepository(session).get_population_zones(
            41.3, 69.3, 500
        )
        session = make_async_session(scalars_result=zones)
        result_large = await DataRepository(session).get_population_zones(
            41.3, 69.3, 5000
        )
        assert len(result_large) >= len(result_small)


# ── POI ────────────────────────────────────────────────────────────────────────


class TestGetPOIs:
    @pytest.mark.asyncio
    async def test_poi_at_center_included(self):
        poi = make_poi(lat=41.3, lon=69.3)
        session = make_async_session(scalars_result=[poi])
        results = await DataRepository(session).get_pois(41.3, 69.3, 500)
        assert len(results) == 1
        assert results[0]["distance_m"] == pytest.approx(0.0, abs=0.1)

    @pytest.mark.asyncio
    async def test_poi_outside_radius_excluded(self):
        # ~2.2 km uzoqlikda
        poi = make_poi(lat=41.32, lon=69.3)
        session = make_async_session(scalars_result=[poi])
        results = await DataRepository(session).get_pois(41.3, 69.3, 500)
        assert results == []

    @pytest.mark.asyncio
    async def test_results_sorted_by_distance(self):
        near = make_poi(id=1, lat=41.302, lon=69.3)
        far = make_poi(id=2, lat=41.304, lon=69.3)
        session = make_async_session(scalars_result=[far, near])
        results = await DataRepository(session).get_pois(41.3, 69.3, 1000)
        assert results[0]["poi"].id == 1
        assert results[0]["distance_m"] < results[1]["distance_m"]

    @pytest.mark.asyncio
    async def test_result_has_poi_and_distance_keys(self):
        poi = make_poi(lat=41.3, lon=69.3)
        session = make_async_session(scalars_result=[poi])
        results = await DataRepository(session).get_pois(41.3, 69.3, 500)
        assert "poi" in results[0]
        assert "distance_m" in results[0]

    @pytest.mark.asyncio
    async def test_empty_db_returns_empty(self):
        session = make_async_session(scalars_result=[])
        results = await DataRepository(session).get_pois(41.3, 69.3, 500)
        assert results == []

    @pytest.mark.asyncio
    async def test_multiple_pois_all_within_radius(self):
        pois = [make_poi(id=i, lat=41.3 + i * 0.001, lon=69.3) for i in range(4)]
        session = make_async_session(scalars_result=pois)
        results = await DataRepository(session).get_pois(41.3, 69.3, 1000)
        assert len(results) == 4


# ── Mijoz segmentlari ──────────────────────────────────────────────────────────


class TestGetCustomerSegments:
    @pytest.mark.asyncio
    async def test_segment_at_center_included(self):
        seg = make_customer_segment(lat=41.3, lon=69.3)
        session = make_async_session(scalars_result=[seg])
        result = await DataRepository(session).get_customer_segments(41.3, 69.3, 1000)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_segment_outside_radius_excluded(self):
        # ~22 km uzoqlikda
        seg = make_customer_segment(lat=41.5, lon=69.3)
        session = make_async_session(scalars_result=[seg])
        result = await DataRepository(session).get_customer_segments(41.3, 69.3, 1000)
        assert result == []

    @pytest.mark.asyncio
    async def test_multiple_segments_filtered(self):
        near = make_customer_segment(id=1, lat=41.303, lon=69.3)
        far = make_customer_segment(id=2, lat=41.5, lon=69.3)
        session = make_async_session(scalars_result=[near, far])
        result = await DataRepository(session).get_customer_segments(41.3, 69.3, 1000)
        assert len(result) == 1
        assert result[0].id == 1

    @pytest.mark.asyncio
    async def test_empty_db_returns_empty(self):
        session = make_async_session(scalars_result=[])
        result = await DataRepository(session).get_customer_segments(41.3, 69.3, 1000)
        assert result == []


# ── Bozor tahminlari ───────────────────────────────────────────────────────────


class TestGetMarketEstimates:
    @pytest.mark.asyncio
    async def test_returns_estimates(self):
        est = make_market_estimate()
        session = make_async_session(scalars_result=[est])
        result = await DataRepository(session).get_market_estimates("restoran")
        assert result == [est]

    @pytest.mark.asyncio
    async def test_empty_when_niche_not_found(self):
        session = make_async_session(scalars_result=[])
        result = await DataRepository(session).get_market_estimates("mavjud_emas")
        assert result == []

    @pytest.mark.asyncio
    async def test_multiple_estimates_returned(self):
        ests = [make_market_estimate(id=i) for i in range(5)]
        session = make_async_session(scalars_result=ests)
        result = await DataRepository(session).get_market_estimates("restoran")
        assert len(result) == 5

    @pytest.mark.asyncio
    async def test_executes_exactly_one_query(self):
        session = make_async_session(scalars_result=[])
        await DataRepository(session).get_market_estimates("restoran")
        session.execute.assert_called_once()


class TestGetMarketEstimateByLocation:
    @pytest.mark.asyncio
    async def test_returns_estimate_when_found(self):
        est = make_market_estimate()
        session = make_async_session(scalar_result=est)
        result = await DataRepository(session).get_market_estimate_by_location(
            "restoran", 41.3, 69.3, 1000
        )
        assert result == est

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        session = make_async_session(scalar_result=None)
        result = await DataRepository(session).get_market_estimate_by_location(
            "restoran", 41.3, 69.3, 1000
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_with_calculation_date_executes_query(self):
        session = make_async_session(scalar_result=None)
        await DataRepository(session).get_market_estimate_by_location(
            "restoran", 41.3, 69.3, 1000, calculation_date=date(2025, 4, 25)
        )
        session.execute.assert_called_once()
