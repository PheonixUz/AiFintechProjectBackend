"""
M-A1 Market Sizing agenti.

LangGraph + LangChain orqali ishlaydi (Gemini modeli):
  1. Gemini get_market_data toolni chaqiradi (LangGraph ReAct loop)
  2. Natijalar algoritmga uzatiladi
  3. Gemini yakuniy tahlilni o'zbek tilida yozadi

Arxitektura:
  MarketSizingAgent.run()
    → LangGraph (agent → tools → agent loop)
    → execute_get_market_data() [DB]
    → run_market_sizing() [pure algorithm]
    → Gemini (final synthesis)
    → MarketSizingResponse
"""

import json
import logging
from decimal import Decimal
from typing import Annotated, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.prompts.system import MARKET_SIZING_SYSTEM
from app.algorithms.market_sizing import (
    MarketSizingInput,
    MarketSizingResult,
    run_market_sizing,
)
from app.config import settings
from app.mcp.tools.market import execute_get_market_data
from app.schemas.request import MarketSizingRequest
from app.schemas.response import MarketSizingResponse

logger = logging.getLogger(__name__)

_MODEL = "gemini-2.0-flash"
_DEFAULT_BENCHMARK = {
    "avg_monthly_revenue_uzs": "50000000",
    "median_monthly_revenue_uzs": "40000000",
    "gross_margin_pct": 0.30,
    "annual_growth_rate_pct": 0.08,
    "avg_employee_count": 3.0,
}


class _State(TypedDict):
    messages: Annotated[list, add_messages]


def _build_user_message(req: MarketSizingRequest) -> str:
    return (
        f"Quyidagi biznes uchun TAM/SAM/SOM bozor hajmini hisoblang:\n"
        f"  Nisha        : {req.niche}\n"
        f"  MCC kod      : {req.mcc_code}\n"
        f"  Lokatsiya    : lat={req.lat}, lon={req.lon}\n"
        f"  Radius       : {req.radius_m} metr\n"
        f"  Shahar       : {req.city}\n"
        f"  Yil          : {req.year}\n"
        f"  Kapital      : {req.capital_uzs:,} UZS\n\n"
        "get_market_data toolni chaqiring va natijalar asosida tahlil bering."
    )


def _build_algorithm_input(
    market_data: dict,
    quality_factor: float = 1.0,
) -> MarketSizingInput:
    bm = market_data.get("benchmark") or _DEFAULT_BENCHMARK
    return MarketSizingInput(
        tam_transactions_uzs=Decimal(market_data["tam_transactions_uzs"]),
        sam_transactions_uzs=Decimal(market_data["sam_transactions_uzs"]),
        competitor_count_city=market_data["competitor_count_city"],
        competitor_count_radius=market_data["competitor_count_radius"],
        avg_monthly_revenue_uzs=Decimal(bm["avg_monthly_revenue_uzs"]),
        median_monthly_revenue_uzs=Decimal(bm["median_monthly_revenue_uzs"]),
        annual_growth_rate_pct=bm["annual_growth_rate_pct"],
        gross_margin_pct=bm["gross_margin_pct"],
        transaction_sample_size=market_data["transaction_sample_size"],
        quality_factor=quality_factor,
    )


def _build_synthesis_prompt(
    req: MarketSizingRequest, result: MarketSizingResult
) -> str:
    def m(v: Decimal) -> str:
        return f"{float(v) / 1_000_000:.1f} mln UZS"

    tam_range = f"{m(result.tam_low_uzs)}–{m(result.tam_high_uzs)}"
    sam_range = f"{m(result.sam_low_uzs)}–{m(result.sam_high_uzs)}"
    som_range = f"{m(result.som_low_uzs)}–{m(result.som_high_uzs)}"
    capital_m = f"{float(req.capital_uzs) / 1_000_000:.1f} mln UZS"

    return (
        f"Hisoblash tugadi. {req.niche} biznesini "
        f"{req.city} shahridagi lokatsiya uchun baholang:\n\n"
        f"  TAM: {m(result.tam_uzs)} ({tam_range})\n"
        f"  SAM: {m(result.sam_uzs)} ({sam_range})\n"
        f"  SOM: {m(result.som_uzs)} ({som_range})\n"
        f"  Bozor o'sishi: {result.market_growth_rate_pct * 100:.1f}%/yil\n"
        f"  Raqobatchilar: {result.competitor_count_radius} ta\n"
        f"  Bozor ulushi: {result.market_share_pct:.1f}%\n"
        f"  Yalpi marja: {result.gross_margin_pct * 100:.0f}%\n"
        f"  Ishonch: {result.confidence_score:.0%}\n"
        f"  Kapital: {capital_m}\n\n"
        "O'zbek tilida qisqa tahlil (3–5 gap): "
        "SOM kapitalga nisbatan, nisha perspektivlimi, xavf."
    )


class MarketSizingAgent:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _make_tools(self) -> list:
        session = self._session

        @tool
        async def get_market_data(
            mcc_code: str,
            niche: str,
            lat: float,
            lon: float,
            radius_m: float,
            city: str,
            year: int,
        ) -> str:
            """Bazadan TAM/SAM tranzaksiyalari, raqobatchilar va benchmark oladi."""
            result = await execute_get_market_data(
                session,
                mcc_code=mcc_code,
                niche=niche,
                lat=lat,
                lon=lon,
                radius_m=radius_m,
                city=city,
                year=year,
            )
            return json.dumps(result, ensure_ascii=False)

        return [get_market_data]

    def _build_graph(self, tools: list):
        llm = ChatGoogleGenerativeAI(
            model=_MODEL,
            google_api_key=settings.google_api_key,
        )
        llm_with_tools = llm.bind_tools(tools)

        async def call_model(state: _State) -> dict:
            response = await llm_with_tools.ainvoke(state["messages"])
            logger.debug("Gemini response type=%s", type(response).__name__)
            return {"messages": [response]}

        def should_continue(state: _State) -> str:
            last = state["messages"][-1]
            if getattr(last, "tool_calls", None):
                return "tools"
            return END

        graph = StateGraph(_State)
        graph.add_node("agent", call_model)
        graph.add_node("tools", ToolNode(tools))
        graph.set_entry_point("agent")
        graph.add_conditional_edges("agent", should_continue)
        graph.add_edge("tools", "agent")

        return graph.compile()

    async def run(self, req: MarketSizingRequest) -> MarketSizingResponse:
        tools = self._make_tools()
        graph = self._build_graph(tools)

        result = await graph.ainvoke(
            {
                "messages": [
                    SystemMessage(content=MARKET_SIZING_SYSTEM),
                    HumanMessage(content=_build_user_message(req)),
                ]
            }
        )

        # ToolMessage dan market_data ni ajratib olish
        market_data: dict | None = None
        for msg in result["messages"]:
            if isinstance(msg, ToolMessage):
                try:
                    market_data = json.loads(msg.content)
                except (json.JSONDecodeError, TypeError):
                    pass
                break

        if market_data is None:
            raise RuntimeError("Agent get_market_data toolni chaqirmadi")

        # Keshdan qaytarish
        if market_data.get("cached_estimate"):
            cached = market_data["cached_estimate"]
            analysis_text = self._last_ai_text(result["messages"])
            bm = market_data.get("benchmark") or _DEFAULT_BENCHMARK
            return MarketSizingResponse(
                niche=req.niche,
                city=req.city,
                tam_uzs=Decimal(cached["tam_uzs"]),
                sam_uzs=Decimal(cached["sam_uzs"]),
                som_uzs=Decimal(cached["som_uzs"]),
                tam_low_uzs=Decimal(cached["tam_uzs"]) * Decimal("0.70"),
                tam_high_uzs=Decimal(cached["tam_uzs"]) * Decimal("1.30"),
                sam_low_uzs=Decimal(cached["sam_uzs"]) * Decimal("0.70"),
                sam_high_uzs=Decimal(cached["sam_uzs"]) * Decimal("1.30"),
                som_low_uzs=Decimal(cached["som_uzs"]) * Decimal("0.70"),
                som_high_uzs=Decimal(cached["som_uzs"]) * Decimal("1.30"),
                market_share_pct=round(
                    100 / (market_data["competitor_count_radius"] + 1), 2
                ),
                market_growth_rate_pct=bm["annual_growth_rate_pct"],
                gross_margin_pct=bm["gross_margin_pct"],
                competitor_count_radius=market_data["competitor_count_radius"],
                confidence_score=cached["confidence_score"],
                data_weight=1.0,
                methodology_notes={
                    "source": "cache",
                    "date": cached["calculation_date"],
                },
                analysis_summary=analysis_text,
                from_cache=True,
            )

        # Algorithm hisoblash
        algo_input = _build_algorithm_input(market_data)
        algo_result = run_market_sizing(algo_input)

        # Gemini tahlili
        llm = ChatGoogleGenerativeAI(
            model=_MODEL,
            google_api_key=settings.google_api_key,
        )
        synthesis = await llm.ainvoke(
            [
                SystemMessage(content=MARKET_SIZING_SYSTEM),
                HumanMessage(content=_build_synthesis_prompt(req, algo_result)),
            ]
        )
        analysis_text = synthesis.content if isinstance(synthesis.content, str) else ""

        return MarketSizingResponse(
            niche=req.niche,
            city=req.city,
            tam_uzs=algo_result.tam_uzs,
            sam_uzs=algo_result.sam_uzs,
            som_uzs=algo_result.som_uzs,
            tam_low_uzs=algo_result.tam_low_uzs,
            tam_high_uzs=algo_result.tam_high_uzs,
            sam_low_uzs=algo_result.sam_low_uzs,
            sam_high_uzs=algo_result.sam_high_uzs,
            som_low_uzs=algo_result.som_low_uzs,
            som_high_uzs=algo_result.som_high_uzs,
            market_share_pct=algo_result.market_share_pct,
            market_growth_rate_pct=algo_result.market_growth_rate_pct,
            gross_margin_pct=algo_result.gross_margin_pct,
            competitor_count_radius=algo_result.competitor_count_radius,
            confidence_score=algo_result.confidence_score,
            data_weight=algo_result.data_weight,
            methodology_notes=algo_result.methodology_notes,
            analysis_summary=analysis_text,
            from_cache=False,
        )

    @staticmethod
    def _last_ai_text(messages: list) -> str:
        for msg in reversed(messages):
            if not isinstance(msg, (HumanMessage, ToolMessage, SystemMessage)):
                content = getattr(msg, "content", "")
                if isinstance(content, str):
                    return content
        return ""
