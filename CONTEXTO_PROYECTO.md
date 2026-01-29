# PROYECTO: NBA VIBECODING PREDICTOR - PROJECT PHOENIX

## 1. OBJETIVO GLOBAL
Crear una plataforma de predicción e inversión deportiva para la NBA que combina modelos numéricos avanzados (XGBoost) con análisis cualitativo de IA (Groq/Llama), integrando un sistema de gestión de bankroll ("Reto Escalera") y seguimiento histórico.

## 2. ARQUITECTURA DEL SISTEMA

### A. Backend (FastAPI)
- **`main.py`**: Punto de entrada de la API. Gestiona endpoints de predicción, historia y el reto escalera.
- **`prediction_api.py`**: Capa de abstracción para cargar modelos XGBoost y generar probabilidades base.
- **`history_db.py`**: Gestión de la base de datos de historial (`Data/history.db`). Implementa **Read-Through Caching** para optimizar velocidad.
- **`ladder/` (Módulo Phoenix)**:
  - **`main_ladder.py`**: Orquestador del reto escalera (Ladder V2).
  - **`strategy_engine.py`**: Lógica de selección de apuestas y gestión de riesgo.
  - **`groq_agent.py`**: Agente de IA para generar narrativas y tickets.

### B. Datos y Persistencia
- **`Data/TeamData.sqlite`**: Datos históricos de equipos y estadísticas (Base del modelo XGBoost).
- **`Data/history.db`**: Historial global de predicciones diarias con resultados (Win/Loss) y Profit.
- **`ladder_v2.db`**: Persistencia específica para el Reto Escalera (Tickets, Steps, Bankroll).
- **`Models/XGBoost_Models/`**: Modelos entrenados (.json) y calibradores (.pkl).

### C. Frontend (Single Page App)
- **`static/index.html`**: Dashboard interactivo moderno.
  - **Tablero de Predicciones**: Muestra partidos de hoy con EVs, probs y análisis IA.
  - **Historial**: Visualización de rendimiento pasado.
  - **Reto Escalera**: Interfaz dedicada para el seguimiento del reto de inversión.

## 3. FLUJOS PRINCIPALES

### 1. Predicción Diaria (`/predict-today`)
1. **Cache Check**: Verifica si ya existen predicciones para hoy en `history.db`.
2. **Generación (Cache Miss)**:
   - Descarga partidos de SBR (Scraper).
   - Ejecuta modelos XGBoost.
   - Enriquece con análisis de noticias (Groq + DuckDuckGo).
   - Guarda en `history.db` como 'PENDING'.
3. **Respuesta**: Devuelve objetos `MatchPrediction` al frontend.

### 2. Reto Escalera (Project Phoenix)
- Genera tickets diarios optimizados (Parlays de 2-3 patas o apuestas directas de alto valor).
- Gestiona el bankroll y los pasos de la escalera.
- Almacena y visualiza tickets históricos.

## 4. REGLAS Y MANTENIMIENTO
1. **Modelos**: Los modelos XGBoost deben estar en `Models/`.
2. **Entorno**: Requiere `.env` con `GROQ_API_KEY`.
3. **Limpieza**: Scripts temporales deben eliminarse. Mantener la raíz limpia.
4. **Dependencias**: `requirements.txt` define el entorno Python.

## 5. ESTADO ACTUAL (Enero 2026)
- **Optimización**: Carga de predicciones instantánea (<500ms) gracias al cache DB.
- **Historial**: Backfill completo para Enero 2026.
- **Frontend**: Totalmente funcional con modo oscuro y diseño responsivo.