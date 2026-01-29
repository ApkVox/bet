# CONTEXTO DEL PROYECTO - NBA VibeCoding Predictor

## 🎯 Objetivo
Sistema de predicciones NBA que combina modelos de Machine Learning (XGBoost) con razonamiento de IA (Groq/Llama 3) para ofrecer un dashboard de análisis deportivo.

## 🏗️ Arquitectura Minimalista

### Backend (Python + FastAPI)
- **`main.py`**: Punto de entrada de la API. Orquesta la carga de modelos, búsqueda de noticias y análisis de IA.
- **`prediction_api.py`**: Interfaz con los modelos XGBoost. Maneja la extracción de características desde `TeamData.sqlite`.
- **`history_db.py`**: Gestiona la persistencia en `history.db`. Implementa un **Read-Through Cache** para predicciones diarias.

### Frontend (Vanilla JS SPA)
- Dashboard de una sola página en `static/index.html`.
- Vistas principales: **Predicciones** (Hoy) e **Historial** (Pasado).
- Integración visual con logos de la NBA y análisis de IA en tiempo real.

### Persistencia (SQLite)
- **`Data/history.db`**: Almacena el historial de predicciones, resultados y cache diaria.
- **`Data/TeamData.sqlite`**: Base de datos con estadísticas históricas de equipos para alimentar el modelo.

## 🔄 Flujos Críticos

1.  **Carga de Predicciones**:
    - El cliente solicita `/predict-today`.
    - El sistema busca en `history.db`.
    - Si no existe (MISS), ejecuta el motor XGBoost, busca noticias en DuckDuckGo, aplica análisis con Groq, y guarda el resultado.
    - Si existe (HIT), devuelve el cache instantáneamente (<100ms).

2.  **Sincronización de Resultados**:
    - Se invoca `/update-history`.
    - El sistema compara predicciones pendientes con resultados reales y actualiza el estado (`WIN`/`LOSS`).

## 🛠️ Reglas de Desarrollo
- **Backend**: Mantener `main.py` limpio de lógica de base de datos directa (usar `history_db.py`).
- **Frontend**: Usar CSS Vanilla y evitar dependencias externas pesadas.
- **Limpieza Absoluta**: Se han eliminado todos los módulos no funcionales: **Escalera, Live, Bankroll, Rendimiento, Configuración**. La app es estrictamente predictiva.

---
**Estado**: Ultra-Minimalista / Funcional
**Última actualización**: 2026-01-29