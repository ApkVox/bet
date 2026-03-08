# La Fija - Documentación para Agentes IA

> Documento optimizado para que un agente de IA comprenda el proyecto, su arquitectura y el estado de sincronización con GitHub.

---

## 1. Resumen del Proyecto

**Nombre:** La Fija  
**Tipo:** Sistema de predicciones deportivas con ML  
**Deportes:** NBA (completo) | Fútbol europeo (parcial, sin noticias)  
**Stack:** Python 3.11, FastAPI, SQLite, XGBoost, Poisson, DeepSeek  
**Hosting:** Render (API) + GitHub Actions (job diario)

---

## 2. Arquitectura

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  GitHub Actions │────▶│ generate_daily_  │────▶│  Data/history.  │
│  (cron 8h,15h   │     │ job.py           │     │  db (SQLite)    │
│   UTC)           │     │ - NBA (XGBoost)  │     │                 │
└─────────────────┘     │ - Fútbol (Poisson)│     └────────┬────────┘
                        │ - Noticias NBA    │              │
                        │   (DeepSeek)      │              │
                        │ - Recomendaciones │              ▼
                        └──────────────────┘     ┌─────────────────┐
                                                 │  Render (API)    │
                                                 │  main.py         │
                                                 │  read-only       │
                                                 └────────┬────────┘
                                                          │
                                                          ▼
                                                 ┌─────────────────┐
                                                 │  Frontend SPA    │
                                                 │  static/         │
                                                 └─────────────────┘
```

---

## 3. Flujos Principales

### 3.1 Job Diario (GitHub Actions)
1. `generate_daily_job.py` se ejecuta
2. **NBA:** sbrscrape → XGBoost → predicciones → `history_db.save_prediction`
3. **Fútbol:** footy → Poisson → `history_db.save_football_prediction`
4. **Noticias NBA:** `news_agent.fetch_news_for_matches` (DeepSeek + DuckDuckGo)
5. **Recomendaciones:** `recommendations.generate_recommendations` (DeepSeek)
6. Commit + push de `Data/history.db` al repo

### 3.2 API (Render)
- `main.py` sirve predicciones desde SQLite (read-only)
- Endpoints: `/predict-today`, `/predict-football`, `/api/news/*`, `/api/recommendations/*`
- Config persistente en Supabase si `DATABASE_URL` está definida

### 3.3 Noticias (solo NBA)
- `news_agent.py`: DuckDuckGo busca → DeepSeek sintetiza → JSON con headline, key_points, injuries
- Sin noticias para fútbol (sistema incompleto)

---

## 4. Estructura de Archivos Clave

| Archivo | Rol |
|---------|-----|
| `main.py` | API FastAPI, endpoints, rutas estáticas |
| `generate_daily_job.py` | Orquestador del job diario (NBA, fútbol, noticias, recomendaciones) |
| `prediction_api.py` | Modelo XGBoost NBA, `predict_games()` |
| `football_api.py` | Modelo Poisson fútbol, `predict_match()` |
| `footy/poisson_predictor.py` | Lógica Poisson |
| `news_agent.py` | Noticias NBA con DeepSeek + DuckDuckGo |
| `recommendations.py` | Recomendaciones parlay con DeepSeek |
| `history_db.py` | Acceso a SQLite (predictions, football_predictions, match_news, daily_recommendations) |
| `config_store.py` | Persistencia Supabase o archivos (admin, tema, promo) |
| `admin_auth.py` | Auth admin, JWT, rate limit |
| `site_settings.py` | Tema, branding, features |
| `promo_generator.py` | Generación de imágenes promocionales |
| `production_server.py` | Punto de entrada uvicorn, carga `.env` |
| `Dockerfile` | Imagen para Render |
| `.github/workflows/daily_prediction.yml` | Cron diario |
| `.github/workflows/keep-alive.yml` | Ping a Render |

---

## 5. Variables de Entorno

| Variable | Uso | Dónde |
|----------|-----|-------|
| `DEEPSEEK_API_KEY` | Noticias y recomendaciones | GitHub Secrets, `.env` local |
| `ODDS_API_KEY` | Cuotas (opcional) | GitHub Secrets |
| `DATABASE_URL` | Supabase para config persistente | Render |
| `PORT` | Puerto del servidor | Render (8080 local) |

---

## 6. Archivos NO Sincronizados con GitHub

### 6.1 Sin trackear (untracked) — No añadidos al repo

| Archivo | Motivo |
|---------|--------|
| `backfill_odds_historical.py` | Script de backfill local, no parte del flujo productivo |
| `backtest_parlay.py` | Script de backtest, análisis interno |
| `backtest_singles.py` | Script de backtest singles |
| `backtest_result.json` | Resultado de backtest, datos temporales |
| `docs/BACKTEST_COMBINADA_2026.md` | Documentación de backtest, no crítica para deploy |
| `docs/ROADMAP_10M.md` | Roadmap interno, no código |

**Acción sugerida:** Si un agente necesita estos archivos, están en el workspace local. Para subirlos: `git add <archivo>` y commit.

### 6.2 En .gitignore — Nunca se suben por diseño

| Patrón/Archivo | Motivo |
|----------------|--------|
| `.env` | Contiene API keys (DEEPSEEK_API_KEY). Seguridad. |
| `.env.*` (excepto `.env.example`) | Credenciales |
| `__pycache__/` | Bytecode Python generado |
| `admin_auth.json` | Hash de contraseña admin, sensible |
| `admin_settings.json` | Config local (si no hay Supabase) |
| `site_settings.json` | Idem |
| `promo_config.json` | Config del editor promo (si no hay Supabase) |
| `password_reset_tokens.json` | Tokens de recuperación |

### 6.3 Modificados localmente pero en conflicto con remoto

| Archivo | Situación |
|---------|-----------|
| `Data/history.db` | El bot de GitHub Actions hace commit+push de su versión. Local puede divergir. Usar `git pull` con cuidado (LFS). |
| `Data/Bankroll.sqlite` | Datos locales de bankroll, no versionado en el flujo principal |

---

## 7. Decisiones de Diseño Relevantes

1. **Solo DeepSeek:** Se eliminó Groq por errores 413/429. Todo el LLM pasa por DeepSeek.
2. **Noticias solo NBA:** Fútbol no tiene agente de noticias (sistema incompleto).
3. **GitOps para history.db:** El job diario commitea la BD al repo. Render sirve desde esa BD.
4. **Supabase para config:** En Render free el filesystem es efímero. Admin, tema y promo se guardan en Supabase si `DATABASE_URL` está definida.
5. **Promo preview POST:** Se usa POST en lugar de GET para evitar 413 por URL larga en Render.

---

## 8. Comandos Útiles

```bash
# Local
pip install -r requirements.txt
python production_server.py

# Refrescar noticias (local)
curl -X POST http://localhost:8080/api/news/refresh

# Ejecutar job completo (local)
python generate_daily_job.py
```

---

## 9. Repositorio

- **URL:** https://github.com/ApkVox/bet
- **Rama principal:** main
- **Última sincronización:** Verificar con `git status` y `git log -1`
