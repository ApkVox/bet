# 🏀 NBA Predictor AI

> **Tu Analista Deportivo Inteligente:** Un sistema avanzado que fusiona Machine Learning con Inteligencia Artificial Generativa para ofrecer predicciones de la NBA con profundidad táctica y precisión estadística.

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![XGBoost](https://img.shields.io/badge/XGBoost-2.0+-FF6B6B?style=for-the-badge&logo=xgboost&logoColor=white)
![Groq](https://img.shields.io/badge/Groq-Llama_3.3-f55036?style=for-the-badge&logo=meta&logoColor=white)
![Status](https://img.shields.io/badge/Estado-Producción-success?style=for-the-badge)

---

## 📖 Tabla de Contenidos

- [Descripción General](#-descripción-general)
- [Características Principales](#-características-principales)
- [Estructura del Proyecto](#-estructura-del-proyecto)
- [Instalación](#-instalación)
- [Uso](#-uso)
- [API](#-api)
- [Despliegue](#-despliegue)

---

## 📋 Descripción General

**NBA Predictor AI** es un ecosistema completo de predicción deportiva que combina:

1. **Motor ML (XGBoost):** Modelo entrenado con 68.9% de precisión en datos históricos NBA.
2. **IA Narrativa (Llama 3.3 vía Groq):** Análisis contextual de lesiones, rachas y factores cualitativos.
3. **Gestión de Riesgo:** Criterio de Kelly, filtros de EV y protección de bankroll.

---

## ✨ Características Principales

| Característica | Descripción |
|:---|:---|
| 🧠 **Predicciones Híbridas** | ML + IA para predicciones explicables |
| 📊 **Dashboard Interactivo** | Interfaz glassmorphism, responsive, dark mode |
| 💰 **Gestión de Bankroll** | Kelly Criterion, EV, stake óptimo |
| 📜 **Historial Completo** | Tracking de predicciones con WIN/LOSS/ROI |
| ⚡ **Cache Inteligente** | Respuestas < 500ms con SQLite |
| 🔒 **Shadow Mode** | Validación sin riesgo antes de ir live |

---

## 📂 Estructura del Proyecto

```
bet/
├── main.py              # FastAPI server principal
├── prediction_api.py    # Motor de predicción XGBoost
├── history_db.py        # Persistencia de historial
├── config.toml          # Configuración del sistema
├── requirements.txt     # Dependencias Python
├── Dockerfile           # Contenedor Docker
│
├── Data/                # Bases de datos SQLite
│   ├── TeamData.sqlite  # Estadísticas de equipos
│   ├── history.db       # Historial de predicciones
│   └── Bankroll.sqlite  # Estado del bankroll
│
├── Models/              # Modelos XGBoost entrenados
├── src/                 # Módulos internos
│   ├── BankrollEngine/  # Gestión de capital
│   ├── Services/        # Servicios de riesgo
│   └── ...
│
├── static/              # Frontend (index.html)
├── tests/               # Tests unitarios
└── docs/                # Documentación técnica
```

---

## 🚀 Instalación

### Requisitos
- Python 3.11+
- Git

### Pasos

```bash
# 1. Clonar repositorio
git clone https://github.com/ApkVox/bet.git
cd bet

# 2. Crear entorno virtual
python -m venv venv
.\venv\Scripts\activate  # Windows
source venv/bin/activate # Linux/Mac

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env y añadir GROQ_API_KEY

# 5. Ejecutar
python main.py
```

Visita `http://localhost:8000`

---

## 🎮 Uso

1. **Predicciones del día:** Página principal muestra partidos con probabilidades
2. **Más Datos:** Click en cualquier partido para análisis detallado
3. **Filtrar:** "Solo mejores oportunidades" muestra solo EV positivo
4. **Historial:** Pestaña para ver rendimiento pasado (WIN/LOSS)

---

## 📡 API

Documentación completa en `/docs` (Swagger UI).

| Método | Endpoint | Descripción |
|:---:|:---|:---|
| `GET` | `/pronosticos-hoy` | Predicciones del día |
| `GET` | `/history/full` | Historial completo |
| `GET` | `/match-details/{home}/{away}` | Análisis de partido |
| `POST` | `/update-history` | Actualizar resultados |
| `GET` | `/bankroll/status` | Estado del bankroll |

---

## 🌐 Despliegue

### Render (Producción)

El proyecto está desplegado en: **https://bet-7b8l.onrender.com**

### Docker

```bash
docker build -t nba-predictor .
docker run -p 8000:8000 --env-file .env nba-predictor
```

### Keep-Alive

El workflow `.github/workflows/keep-alive.yml` hace ping cada 10 minutos para evitar que Render duerma el servidor.

---

## 📝 Licencia

MIT License - Libre uso, modificación y distribución.

> **⚠️ AVISO:** Esta herramienta es para fines educativos. Las predicciones deportivas conllevan riesgos financieros. No apuestes dinero que no puedas permitirte perder.

---

<div align="center">
  <h3>Hecho con ❤️, Código y Baloncesto 🏀</h3>
</div>
