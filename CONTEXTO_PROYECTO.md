# CONTEXTO DEL PROYECTO - Courtside AI

## 🎯 Objetivo
Sistema de predicciones NBA que combina modelos de Machine Learning (XGBoost) con razonamiento de IA (Groq/Llama 3) para ofrecer un dashboard de análisis deportivo.

## 🏗️ Arquitectura

### Backend (Python + FastAPI)
- **`main.py`**: Punto de entrada de la API. Orquesta predicciones, scheduler automático y análisis de IA.
- **`prediction_api.py`**: Motor XGBoost con extracción de features desde `TeamData.sqlite`.
- **`history_db.py`**: Persistencia en `history.db` con Read-Through Cache.

### Frontend (Vanilla JS SPA)
- **Diseño Apple Bento Grid** con tarjetas redondeadas y sombras suaves.
- **Modo Oscuro/Claro** con toggle y auto-detect del sistema (prefers-color-scheme).
- **Responsive Design** mobile-first con navegación bottom en móviles.
- Vistas: **Predicciones** (Hoy) + **Historial** (Pasado).

### Persistencia (SQLite)
- **`Data/history.db`**: Historial de predicciones desde 2026-01-27.
- **`Data/TeamData.sqlite`**: Estadísticas históricas de equipos NBA.

## 🔄 Flujos Críticos

1. **Carga de Predicciones**:
   - Cliente → `/predict-today`
   - Sistema busca en cache (history.db)
   - MISS: XGBoost + Groq AI → Guarda resultado
   - HIT: Respuesta instantánea (<100ms)

2. **Sincronización de Resultados**:
   - Scheduler automático cada 15 minutos
   - Manual: `GET /api/update-pending`
   - Actualiza `PENDING` → `WIN`/`LOSS`

## 🎨 Diseño Frontend

- **Layout**: CSS Grid con Bento Cards
- **Colores Light**: `#f5f5f7` bg, `#0071e3` accent
- **Colores Dark**: `#000000` bg, `#0a84ff` accent
- **Tipografía**: Inter/SF Pro Display
- **Border Radius**: 24px (cards), 16px (buttons)
- **Breakpoints**: 480px, 768px, 1024px

## 🛠️ Reglas de Desarrollo
- Backend: Usar `history_db.py` para toda persistencia
- Frontend: CSS Vanilla, sin frameworks externos
- Temas: Usar CSS custom properties (`--variable`)

---
**Estado**: Producción / Apple Bento Grid Design
**Última actualización**: 2026-02-07