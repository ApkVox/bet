# 🏀 NBA VibeCoding Predictor

> **Motor híbrido de predicciones NBA:** Combina XGBoost (análisis numérico) con Groq LLM (análisis narrativo) para predicciones inteligentes.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green?logo=fastapi)
![XGBoost](https://img.shields.io/badge/XGBoost-2.0+-orange)
![Groq](https://img.shields.io/badge/Groq-Llama_3.3_70B-purple)

---

## 📋 Descripción

Este proyecto utiliza un enfoque **VibeCoding** para predicciones de la NBA:

1. **Motor Numérico (XGBoost):** Modelos pre-entrenados con ~69% de accuracy que analizan estadísticas históricas.
2. **Motor Narrativo (Groq LLM):** Llama 3.3 70B genera análisis tácticos explicando el "por qué" de cada predicción.
3. **API REST (FastAPI):** Endpoint simple para obtener predicciones del día.

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
# Copiar el archivo de ejemplo
cp .env.example .env

# Editar con tu API Key de Groq
# Obtén tu key en: https://console.groq.com
```

### 5. Ejecutar la API
```bash
uvicorn main:app --reload
```

La API estará disponible en: `http://localhost:8000`

---

## 📡 Endpoints

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/` | GET | Health check y estado del modelo |
| `/predict-today` | GET | Predicciones de partidos del día |
| `/predict-today?include_ai=false` | GET | Solo predicciones numéricas (sin LLM) |
| `/teams` | GET | Lista de equipos NBA soportados |

### Ejemplo de respuesta `/predict-today`

```json
{
  "date": "2026-01-20",
  "total_games": 3,
  "predictions": [
    {
      "home_team": "Los Angeles Lakers",
      "away_team": "Boston Celtics",
      "winner": "Boston Celtics",
      "win_probability": 58.3,
      "under_over": "OVER",
      "ou_line": 224.5,
      "ou_probability": 54.2,
      "ai_analysis": "Boston llega con 5 victorias consecutivas..."
    }
  ],
  "model_accuracy": "68.9%",
  "status": "✅ Predicciones generadas con XGBoost + Groq AI"
}
```

---

## 🐳 Deploy con Docker

```bash
# Construir imagen
docker build -t nba-vibecoding .

# Ejecutar contenedor
docker run -p 10000:10000 -e GROQ_API_KEY=tu_key nba-vibecoding
```

### Deploy en Render
1. Conecta tu repositorio de GitHub
2. Render detectará el `Dockerfile` automáticamente
3. Añade la variable `GROQ_API_KEY` en el dashboard

---

## 📁 Estructura del Proyecto

```
📦 nba-vibecoding/
├── 📄 main.py           # API FastAPI principal
├── 📄 Dockerfile        # Configuración Docker
├── 📄 requirements.txt  # Dependencias Python
├── 📁 src/              # Código fuente original
│   ├── Predict/         # Runners de predicción
│   ├── Utils/           # Herramientas y diccionarios
│   └── DataProviders/   # Proveedores de datos (sbrscrape)
├── 📁 Data/             # Bases de datos SQLite
│   ├── TeamData.sqlite  # Estadísticas de equipos
│   └── OddsData.sqlite  # Datos de apuestas
└── 📁 Models/           # Modelos pre-entrenados
    └── XGBoost_Models/  # Modelos ML (68.9% accuracy)
```

---

## ⚙️ Stack Tecnológico

| Componente | Tecnología |
|------------|------------|
| Backend | FastAPI + Uvicorn |
| ML Engine | XGBoost + Scikit-learn |
| LLM | Groq API (Llama 3.3 70B) |
| Data | SQLite + Pandas |
| Deploy | Docker + Render |

---

## 📝 Licencia

Este proyecto es para fines educativos y de entretenimiento. Las predicciones no garantizan resultados y no deben usarse para apuestas reales.

---

<p align="center">
  <strong>Hecho con ❤️ y VibeCoding</strong>
</p>
