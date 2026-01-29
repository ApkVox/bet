# 🏀 NBA VibeCoding Predictor

> **Motor híbrido de predicciones NBA:** Combina XGBoost (análisis numérico) con Groq LLM (análisis narrativo) para predicciones inteligentes.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green?logo=fastapi)
![XGBoost](https://img.shields.io/badge/XGBoost-2.0+-orange)
![Groq](https://img.shields.io/badge/Groq-Llama_3.3_70B-purple)

---

## 📋 Descripción

Este proyecto utiliza un enfoque **VibeCoding** para predicciones de la NBA:

1. **Motor Numérico (XGBoost):** Modelos pre-entrenados con ~69% de accuracy que analizan estadísticas históricas de los equipos.
2. **Motor Narrativo (Groq LLM):** Llama 3.3 70B genera análisis tácticos explicando el "por qué" de cada predicción.
3. **Read-Through Cache:** Optimización de carga instantánea mediante persistencia en SQLite para evitar regeneraciones innecesarias y mejorar la velocidad de respuesta (<500ms).

---

## 🚀 Instalación Local

### 1. Clonar el repositorio
```bash
git clone https://github.com/tu-usuario/nba-vibecoding.git
cd nba-vibecoding
```

### 2. Crear entorno virtual
```bash
python -m venv venv

# Windows
.\venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno
```bash
# Crear archivo .env
echo "GROQ_API_KEY=tu_api_key_aquí" > .env
```

### 5. Ejecutar la API
```bash
python main.py
```

La API estará disponible en: `http://localhost:8000`

---

## 📡 Endpoints Principales

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/predict-today` | GET | Predicciones del día (con Cache y AI) |
| `/history/full` | GET | Historial detallado de predicciones pasadas |
| `/history` | GET | Historial de predicciones (versión corta) |
| `/update-history` | POST | Sincroniza resultados de partidos pendientes |

---

## 📁 Estructura del Proyecto

```
📦 nba-vibecoding/
├── 📄 main.py           # API FastAPI principal
├── 📄 prediction_api.py # Motor de predicciones XGBoost
├── 📄 history_db.py     # Gestión de historial y Cache
├── 📁 static/           # Frontend (SPA Dashboard)
├── 📁 Data/             # Bases de datos 
│   ├── history.db       # Historial global y cache
│   └── TeamData.sqlite  # Estadísticas NBA
└── 📁 Models/           # Modelos pre-entrenados (.json / .pkl)
```

---

## ⚙️ Stack Tecnológico

| Componente | Tecnología |
|------------|------------|
| Backend | FastAPI |
| ML Engine | XGBoost + Scikit-learn |
| LLM | Groq API (Llama 3.3 70B) |
| Data | SQLite + Pandas |
| Frontend | HTML5 + CSS3 (Vanilla) + JS |

---

## 📝 Licencia

Este proyecto es para fines educativos y de entretenimiento. Las predicciones no garantizan resultados y no deben usarse para apuestas reales.

---

<p align="center">
  <strong>Hecho con ❤️ y VibeCoding</strong>
</p>
