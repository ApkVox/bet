# CONTEXTO DEL PROYECTO - Courtside AI

## 🎯 Objetivo
Sistema de predicciones deportivas (NBA + Fútbol) que combina modelos de Machine Learning con razonamiento de IA para ofrecer un dashboard de análisis deportivo.

## 🏗️ Arquitectura

### Backend (Python + FastAPI)
- **`main.py`**: Punto de entrada de la API. Orquesta predicciones, scheduler automático, keep-alive y análisis de IA.
- **`prediction_api.py`**: Motor XGBoost (68.9% precisión) con extracción de features desde `TeamData.sqlite`.
- **`football_api.py`**: Motor Poisson para predicciones de fútbol (Premier League + ligas europeas).
- **`footy/poisson_predictor.py`**: Predictor basado en distribución Poisson para scorelines.
- **`history_db.py`**: Persistencia en `history.db` con Read-Through Cache e invalidación automática.

### Frontend (Vanilla JS SPA)
- **Diseño Apple Bento Grid** con tarjetas redondeadas y sombras suaves.
- **Modo Oscuro/Claro** con toggle y auto-detect del sistema.
- **Responsive Design** mobile-first con navegación bottom en móviles.
- **Multi-deporte**: Selector NBA/Fútbol con tarjetas adaptadas (2-way y 3-way).
- Vistas: **Predicciones** (Hoy) + **Historial** (Pasado).

### Persistencia (SQLite)
- **`Data/history.db`**: Historial de predicciones NBA y fútbol.
- **`Data/TeamData.sqlite`**: Estadísticas históricas de equipos NBA.
- **`Data/football/complete_features.csv`**: Datos históricos de fútbol para Poisson.

## 🔄 Flujos Críticos

1. **Carga de Predicciones NBA**:
   - Cliente → `/predict-today`
   - Sistema busca en cache (history.db)
   - MISS: XGBoost + Groq AI → Guarda resultado
   - HIT: Valida cache vs SBR → Respuesta instantánea o regenera

2. **Predicciones Fútbol**:
   - Cliente → `/predict-football`
   - Motor Poisson calcula probabilidades 1X2
   - Guarda en history.db

3. **Scheduler Automático (4 jobs)**:
   - Keep-Alive: self-ping cada 2 min
   - Update Pending: actualiza scores cada 15 min
   - Auto Daily Refresh: valida cache cada 30 min
   - Games Cache Refresh: refresca SBR cada 15 min

4. **Auto-Recovery en Startup**:
   - Carga modelos → Refresca cache → Init DB → Valida predicciones → Scheduler

## 🎨 Diseño Frontend

- **Layout**: CSS Grid con Bento Cards
- **Colores Light**: `#f5f5f7` bg, `#0071e3` accent
- **Colores Dark**: `#000000` bg, `#0a84ff` accent
- **Tipografía**: Inter/SF Pro Display
- **Border Radius**: 24px (cards), 16px (buttons)

## 🛠️ Reglas de Desarrollo
- Backend: Usar `history_db.py` para toda persistencia
- Frontend: CSS Vanilla, sin frameworks externos
- Temas: Usar CSS custom properties (`--variable`)
- Seguridad: No exponer debug logs, usuario no-root en Docker

---
**Estado**: Producción  
**URL**: https://bet-7b8l.onrender.com  
**Última actualización**: 2026-02-09