# ACTAP API Reference / API 速查

> Full OpenAPI schema is auto-generated and available at `/docs` (Swagger UI) and `/openapi.json`.

## Conventions

- All endpoints are prefixed with `/api/`
- All responses are JSON
- Errors follow the unified format (see below)
- Auth: sensitive endpoints require `X-API-Key: <secret>` header
- Tracing: pass `X-Request-ID` to propagate a request ID; otherwise one is generated

### Error response shape

```json
{
  "error_code": "VALIDATION_ERROR",
  "message": "Request validation failed",
  "details": [{"field": "type", "type": "string_pattern_mismatch", "message": "..."}],
  "request_id": "0af7651916cd43dd8448eb211c80319c"
}
```

| Status | error_code | When |
|--------|------------|------|
| 401 | `AUTH_MISSING_API_KEY` | Protected endpoint hit without `X-API-Key` |
| 403 | `AUTH_INVALID_API_KEY` | Wrong API key |
| 422 | `VALIDATION_ERROR` | Pydantic validation failed |
| 429 | `RATE_LIMIT_EXCEEDED` | Per-IP limit exceeded (header `Retry-After` set) |
| 503 | `HTTP_ERROR` | Upstream external API failed |
| 500 | `INTERNAL_ERROR` | Unhandled server error |

## Endpoints

### Health & metrics

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/health` | none | Liveness probe |
| GET | `/api/health/ready` | none | Readiness (DB + cache) |
| GET | `/api/metrics` | none | Prometheus metrics |

### Trade analysis (`/api/trade/...`)

| Method | Path | Query | Description |
|--------|------|-------|-------------|
| GET | `/trend` | `countries`, `products`, `start_year`, `end_year` | Monthly trend points |
| GET | `/country-compare` | — | 10-country radar data |
| GET | `/ranking` | `type=country|product`, `limit=1..50` | Top-N ranking |
| GET | `/sankey` | `year=YYYY` | Sankey diagram |

### AI prediction (`/api/ai/...`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/prediction?country=&horizon=` | LSTM-style forecast |
| GET | `/clustering` | Product clusters |
| GET | `/risk-alerts` | Active risk alerts |

### Tariff (`/api/tariff/...`)

| Method | Path | Body | Description |
|--------|------|------|-------------|
| POST | `/calculate` | `{hs_code, origin_country, target_country, value_usd}` | Compare MFN/RCEP/ACFTA |
| GET | `/common-codes` | — | List common HS codes |

### AI assistant (`/api/chat/...`) 🔒

| Method | Path | Description |
|--------|------|-------------|
| POST | `/ask` | Send message, get reply |
| GET | `/suggestions` | Suggested questions |

### Data assets (`/api/assets/...`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/lineage` | Data lineage graph |
| GET | `/quality` | Data quality metrics |
| GET | `/catalog` | Data asset catalog |

### Data sources (`/api/datasources/...`) 🔒 refresh

| Method | Path | Description |
|--------|------|-------------|
| GET | `/status` | All data sources status |
| GET | `/exchange-rates` | Latest FX rates |
| GET | `/macro/{country_code}` | World Bank macro profile |
| GET | `/comtrade/summary?partner=&year=` | UN Comtrade summary |
| GET | `/commodity-prices` | IMF commodity prices |
| GET | `/imf-validation?partner=&year=` | Comtrade vs IMF cross-check |
| POST | `/refresh` | 🔒 Clear API cache |

### Analytics (`/api/analytics/...`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/burst-radar?partner=&threshold=` | Burst product detection |
| GET | `/risk-dashboard?country=` | Country risk composite |
| GET | `/upstreamness?year=` | Value chain position index |
| GET | `/tariff-savings?partner=` | RCEP savings summary |

## Rate limits

| Scope | Default |
|-------|---------|
| Global (per IP) | 120 req/min |
| `/api/datasources/refresh` + `/api/chat/*` | 10 req/min |
| Headers on success | `X-RateLimit-Limit`, `X-RateLimit-Remaining` |
| Header on 429 | `Retry-After: 60` |

## Response headers (all endpoints)

| Header | Description |
|--------|-------------|
| `X-Request-ID` | Unique request identifier (or echoed from client) |
| `X-Response-Time-Ms` | Server-side processing time |
| `X-RateLimit-Limit` | Current rate limit for the path class |
| `X-RateLimit-Remaining` | Remaining requests in the current window |
