# La Fija - Predicciones Deportivas

Sistema de predicciones deportivas con Machine Learning para NBA y Futbol europeo.

## Arquitectura

- **API (Render)**: FastAPI ultraligera (~50MB RAM) que sirve predicciones pre-calculadas desde SQLite.
- **Motor ML (GitHub Actions)**: XGBoost (NBA) y Poisson (Futbol) se ejecutan diariamente a las 3:00 AM COT.
- **Persistencia**: GitOps - la base de datos `history.db` se commitea al repo automaticamente.
- **Keep-Alive**: Servicio externo (cron-job.org) mantiene Render activo con pings cada 5 minutos.

## Stack Tecnologico

| Capa | Tecnologia |
|---|---|
| Backend | Python 3.11, FastAPI, Uvicorn |
| ML (NBA) | XGBoost, Pandas, sbrscrape |
| ML (Futbol) | Distribucion Poisson, footy |
| Frontend | HTML5, CSS3, JavaScript vanilla |
| Base de Datos | SQLite3 |
| CI/CD | GitHub Actions |
| Hosting | Render (Free Tier) |

## Endpoints

| Ruta | Descripcion |
|---|---|
| `GET /` | Frontend SPA |
| `GET /api/health` | Health check |
| `GET /predict-today` | Predicciones NBA del dia |
| `GET /predict-football` | Predicciones futbol |
| `GET /history/full` | Historial NBA |
| `GET /history/football` | Historial futbol |

## Estructura del Proyecto

```
bet/
├── main.py                  # API FastAPI (read-only, ultraligera)
├── prediction_api.py        # Modelo XGBoost para NBA
├── football_api.py          # Modelo Poisson para futbol
├── history_db.py            # Capa de acceso a SQLite
├── generate_daily_job.py    # Script CRON para GitHub Actions
├── production_server.py     # Punto de entrada de produccion
├── Dockerfile               # Imagen Docker para Render
├── requirements.txt         # Dependencias completas (dev/CI)
├── requirements_prod.txt    # Dependencias minimas (produccion)
├── Data/
│   └── history.db           # Base de datos SQLite
├── Models/                  # Modelos XGBoost entrenados
├── static/
│   ├── index.html           # Frontend SPA
│   └── js/app.js            # Logica del frontend
└── .github/workflows/
    └── daily_prediction.yml # CRON diario (3AM COT)
```

## Despliegue

1. Fork/clone el repositorio
2. Configurar Render con el Dockerfile
3. Habilitar GitHub Actions (Settings > Actions > Workflow permissions > Read and write)
4. Configurar cron-job.org para ping cada 5 min a `/api/health`

## Desarrollo Local

```bash
pip install -r requirements.txt
python production_server.py
# Acceder en http://localhost:8080
```
