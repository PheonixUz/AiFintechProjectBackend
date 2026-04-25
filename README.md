# AI Fintech Platform — KMB

**Коммерческий банк Узбекистана (KMB)** uchun AI-asosidagi biznes tahlil platformasi.

Berilgan biznes nishasi, GPS koordinata va boshlang'ich kapital asosida tizim javob beradi:

> **"Men bu biznesni, bu joyda, hozir ochamanmi?"** — HA/YO'Q tavsiyasi va to'liq tahlil bilan (o'zbek tilida).

---

## Asosiy g'oya

O'z ML modellarimizni o'rgatmaymiz. Buning o'rniga:

1. **Bank tranzaksion ma'lumotlari** (PostgreSQL — MCP Server orqali)
2. **Matematik/statistik algoritmlar** (sof Python funksiyalari)
3. **AI Agent** (Claude `tool_use`) — qaysi modelni ishlatishni o'zi hal qiladi, natijalarni sintez qiladi va yakuniy HA/YO'Q qarorini beradi

---

## Arxitektura

```
POST /api/v1/analyze
  { nisha, koordinata, kapital }
        │
  AgentOrchestrator
    Claude (tool_use loop)
        │
    ┌───┴──────────────────────┐
    │  MCP Tools (DB so'rovlari) │  ←── PostgreSQL
    │  Algorithm Tools (hisob)   │  ←── Sof Python
    └───┬──────────────────────┘
        │
  Yakuniy HA/YO'Q + O'zbek tushuntirish
        │
  AnalysisResponse (JSON)
```

### Qatlamlar

| Qatlam | Joylashuv | Vazifasi |
|---|---|---|
| `api/routes/` | HTTP chegara | So'rovni qabul qilish, javobni serializatsiya qilish |
| `agent/` | AI orkestratsiya | Claude `tool_use` loop; qaysi toolni chaqirishni hal qiladi |
| `mcp/tools/` | DB shluzi | SQL so'rovlarini bajaradigan MCP tools; faqat shu qatlam DB ga tegadi |
| `algorithms/` | Sof matematik | Stateless funksiyalar — I/O yo'q, side-effect yo'q |
| `db/repositories/` | Ma'lumot olish | MCP tools tomonidan chaqiriladigan async SQL so'rovlari |
| `schemas/` | Kontraktlar | So'rov, javob va algoritm uchun Pydantic modellari |

---

## MVP: 5 ta model

| Kod | Nomi | Algoritm | Nima javob beradi |
|---|---|---|---|
| **M-A3** | Saturation Index | Composite index | Nisha qanchalik to'yingan? (0–100) |
| **M-C1** | Location Score | Weighted composite | Bu nuqta qanchalik jozibali? (0–100) |
| **M-D1** | Viability Check | Monte Carlo + break-even | Biznes 2 yildan omon qolishiga ehtimol |
| **M-D3** | ROI Estimator | DCF / NPV / IRR | Investitsiya foydali bo'ladimi? |
| **M-E2** | Churn Prediction | Scoring model | 2 yilda yopilish ehtimoli (%) |

---

## Agent ishlash jarayoni

```
So'rov: { nisha: "Kafe", koordinata: [41.299, 69.240], kapital: 50_000_000 }

Qadam 1 → get_niche_transactions("Kafe", radius=1000)
Qadam 2 → get_competitors(41.299, 69.240, radius=500)
Qadam 3 → get_location_poi(41.299, 69.240)
Qadam 4 → get_sector_benchmarks("Kafe")

Qadam 5 → run_saturation_index(...)  → { score: 72 }
Qadam 6 → run_location_score(...)    → { score: 68 }
Qadam 7 → run_viability_check(...)   → { survival_2y: 0.61, breakeven: 8 oy }
Qadam 8 → run_roi_estimator(...)     → { npv: 12_400_000, roi: 0.248 }
Qadam 9 → run_churn_prediction(...)  → { closure_probability: 0.38 }

Yakuniy: "YO'Q — nisha yuqori to'yingan (72/100), yopilish ehtimoli 38%."
```

---

## Loyiha tuzilmasi

```
AiFintechProject/
├── pyproject.toml
├── uv.lock
├── .env.example
├── docs/
│   ├── problem.txt
│   └── Ai_Models.md
└── src/
    └── app/
        ├── main.py
        ├── config.py
        ├── api/routes/analyze.py       # POST /api/v1/analyze
        ├── schemas/
        │   ├── request.py              # AnalysisRequest
        │   └── response.py             # AnalysisResponse
        ├── agent/
        │   ├── orchestrator.py         # Agent loop (tool_use)
        │   ├── tool_registry.py
        │   └── prompts/
        │       ├── system.py           # Prompt caching bilan
        │       └── decision.py
        ├── mcp/
        │   ├── server.py
        │   └── tools/
        │       ├── market.py
        │       ├── location.py
        │       ├── financial.py
        │       └── competition.py
        ├── algorithms/
        │   ├── saturation_index.py     # M-A3
        │   ├── location_score.py       # M-C1
        │   ├── viability_check.py      # M-D1
        │   ├── roi_estimator.py        # M-D3
        │   └── churn_prediction.py     # M-E2
        └── db/
            ├── connection.py
            ├── models/
            └── repositories/

tests/
├── conftest.py
├── unit/algorithms/
└── integration/
```

---

## O'rnatish va ishga tushirish

### Talablar

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) paket menejeri
- PostgreSQL
- Redis

### O'rnatish

```bash
# Dependencylarni o'rnatish
uv sync

# Dev dependencylar bilan
uv sync --group dev
```

### Muhit o'zgaruvchilarini sozlash

```bash
cp .env.example .env
# .env faylini to'ldiring:
# DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/fintech_db
# ANTHROPIC_API_KEY=sk-ant-...
# REDIS_URL=redis://localhost:6379
```

### Serverni ishga tushirish

```bash
uv run uvicorn app.main:app --reload --app-dir src
```

API `http://localhost:8000` manzilida ishlaydi.

---

## API

### `POST /api/v1/analyze`

**So'rov:**
```json
{
  "nisha": "Kafe",
  "koordinata": [41.299698, 69.240073],
  "kapital": 50000000
}
```

**Javob:**
```json
{
  "qaror": "YO'Q",
  "tushuntirish": "Nisha yuqori to'yingan (72/100), yopilish ehtimoli 38%...",
  "skorlar": {
    "saturation_index": 72,
    "location_score": 68,
    "survival_2y": 0.61,
    "roi": 0.248,
    "closure_probability": 0.38
  }
}
```

---

## Testlar

```bash
# Barcha testlar
uv run pytest

# Faqat unit testlar (DB kerak emas)
uv run pytest tests/unit/

# Faqat integration testlar (real PostgreSQL kerak)
uv run pytest tests/integration/

# Bitta fayl
uv run pytest tests/unit/algorithms/test_viability.py

# Coverage bilan
uv run pytest --cov=src/app --cov-report=term-missing
```

---

## Kod sifati

```bash
uv run ruff check src/ tests/
uv run ruff format src/ tests/
```

---

## Texnologiyalar

| Texnologiya | Maqsad |
|---|---|
| **FastAPI** | HTTP API |
| **Claude Sonnet** (`tool_use`) | AI Agent orkestratsiyasi |
| **MCP** | Agent va DB o'rtasida protokol |
| **PostgreSQL + asyncpg** | Tranzaksion ma'lumotlar bazasi |
| **Redis** | Agent natijalarini keshlash |
| **NumPy / SciPy** | Monte Carlo, statistik hisob-kitob |
| **Pydantic** | Ma'lumot validatsiyasi va sxemalar |
| **uv** | Paket va virtual muhit menejeri |
| **pytest** | Test framework |

---

## Litsenziya

KMB ichki loyihasi. Barcha huquqlar himoyalangan.
