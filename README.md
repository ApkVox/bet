# 🏀⚽ Courtside AI

> **Tu Analista Deportivo Inteligente** — Predicciones NBA y Fútbol con Machine Learning e Inteligencia Artificial

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![XGBoost](https://img.shields.io/badge/XGBoost-2.0+-FF6B6B?style=for-the-badge&logo=xgboost&logoColor=white)

---

## ✨ Características

| Característica | Descripción |
|:---|:---|
| 🎯 **Predicciones NBA** | Modelo XGBoost con 68.9% de precisión |
| ⚽ **Predicciones Fútbol** | Modelo Poisson para Premier League y ligas europeas |
| 🤖 **Análisis IA** | Groq LLM (Llama 3.3 70B) para análisis narrativo |
| 🔄 **Auto-Recovery** | Keep-alive, cache invalidation y auto-refresh |
| 🌓 **Modo Oscuro/Claro** | Toggle de tema con auto-detect del sistema |
| 📱 **Diseño Responsive** | Optimizado para móviles (Bento Grid estilo Apple) |
| 📜 **Historial Completo** | Tracking de WIN/LOSS con filtros |

---

## 🚀 Instalación

```bash
# Clonar
git clone https://github.com/ApkVox/bet.git
cd bet

# Entorno virtual
python -m venv venv
.\venv\Scripts\activate  # Windows

# Dependencias
pip install -r requirements.txt

# Configurar .env
cp .env.example .env
# Editar .env con tu GROQ_API_KEY

# Ejecutar
python main.py
```

Visita `http://localhost:8000`

---

## 📡 API

| Método | Endpoint | Descripción |
|:---:|:---|:---|
| `GET` | `/predict-today` | Predicciones NBA del día |
| `GET` | `/predict-football` | Predicciones de fútbol (Poisson) |
| `GET` | `/history/full` | Historial completo NBA |
| `GET` | `/history/football` | Historial de fútbol |
| `GET` | `/api/health` | Health check (usado por keep-alive) |
| `GET` | `/api/update-pending` | Sincronizar resultados |

Documentación Swagger: `/docs`

---

## 📂 Estructura

```
bet/
├── main.py              # API FastAPI (endpoints + scheduler)
├── prediction_api.py    # Motor XGBoost (NBA)
├── football_api.py      # Motor Poisson (Fútbol)
├── footy/               # Predictor Poisson
├── history_db.py        # Persistencia SQLite
├── production_server.py # Entry point producción
├── static/
│   ├── index.html       # Frontend SPA
│   └── js/app.js        # Lógica frontend
├── Data/                # Bases de datos y datasets
├── Models/              # Modelos XGBoost entrenados
└── Dockerfile           # Deploy (non-root user)
```

---

## 🔄 Sistema Automático

El servidor incluye 4 jobs automáticos:

| Job | Intervalo | Función |
|:---|:---:|:---|
| 🏓 Keep-Alive | 2 min | Self-ping para evitar sleep de Render |
| 📊 Update Pending | 15 min | Actualiza scores de partidos finalizados |
| 🔄 Auto Daily Refresh | 30 min | Valida predicciones vs datos reales de SBR |
| 🏀 Games Cache Refresh | 15 min | Refresca partidos desde SBR |

**Auto-Recovery**: Al arrancar, ejecuta validación completa y regenera predicciones stale.

---

## 🔒 Seguridad

- Dockerfile con usuario no-root (`appuser`)
- Endpoint de debug protegido con `DEBUG_MODE` env var
- Variables sensibles en `.env` (no versionadas)
- Error messages sanitizados

---

## 🌐 Despliegue

**Producción:** https://bet-7b8l.onrender.com

```bash
docker build -t courtside-ai .
docker run -p 10000:10000 --env-file .env courtside-ai
```

---

> ⚠️ **AVISO:** Herramienta educativa. Las predicciones deportivas conllevan riesgos. No apuestes dinero que no puedas perder.

<div align="center">
  <sub>Hecho con ❤️ 🏀 ⚽</sub>
</div>
