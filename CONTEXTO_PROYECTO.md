# CONTEXTO DEL PROYECTO - La Fija

## Objetivo
Sistema de predicciones deportivas automatizado que utiliza modelos de Machine Learning para generar predicciones diarias de NBA (XGBoost) y futbol europeo (Poisson).

## Arquitectura
- **Backend**: Python/FastAPI como API read-only ultraligera (<50MB RAM)
- **Frontend**: SPA con HTML5/CSS3/JS vanilla
- **Persistencia**: SQLite (history.db) versionada en Git
- **ML Pipeline**: GitHub Actions ejecuta modelos diariamente a las 3AM COT
- **Hosting**: Render Free Tier + cron-job.org para keep-alive

## Flujos Criticos

### Flujo de Prediccion (GitHub Actions - 3AM COT)
1. `generate_daily_job.py` carga modelos XGBoost y Poisson
2. Obtiene juegos del dia via sbrscrape y APIs de futbol
3. Genera predicciones con probabilidades calibradas
4. Actualiza resultados Win/Loss de dias anteriores
5. Guarda todo en `history.db` y hace commit al repo

### Flujo de Consulta (Render - Usuario)
1. Usuario accede a la web
2. API lee predicciones pre-calculadas desde SQLite
3. Sirve datos al frontend sin cargar modelos ML
4. Consumo de memoria: <50MB

## Modelos
- **NBA**: XGBoost con features punto-en-el-tiempo (stats historicas al momento del partido)
- **Futbol**: Distribucion de Poisson para predicciones 1X2

## Zona Horaria
Todo el sistema opera en hora Colombia (UTC-5 / America/Bogota).