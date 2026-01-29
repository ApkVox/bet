# 🏀 NBA VibeCoding Predictor - Project Phoenix

> **Motor híbrido de predicciones NBA:** Combina XGBoost (análisis numérico) con Groq LLM (análisis narrativo) para predicciones inteligentes y gestión de bankroll optimizada.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green?logo=fastapi)
![XGBoost](https://img.shields.io/badge/XGBoost-2.0+-orange)
![Groq](https://img.shields.io/badge/Groq-Llama_3.3_70B-purple)

---

## 📋 Descripción

Este proyecto utiliza un enfoque **VibeCoding** para predicciones de la NBA y gestión de inversiones deportivas:

1. **Motor Numérico (XGBoost):** Modelos pre-entrenados con ~69% de accuracy que analizan estadísticas históricas.
2. **Motor Narrativo (Groq LLM):** Llama 3.3 70B genera análisis tácticos explicando el "por qué" de cada predicción y construye tickets optimizados.
3. **Read-Through Cache:** Optimización de carga instantánea mediante persistencia en SQLite para evitar regeneraciones innecesarias.
4. **Project Phoenix (Reto Escalera):** Sistema de gestión de bankroll compuesto para maximizar beneficios con riesgo controlado.

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

# Editar con tu API Key de Groq en .env
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
| `/history` | GET | Historial de predicciones pasadas |
| `/ladder/v2/{id}/status` | GET | Estado actual del Reto Escalera |
| `/ladder/v2/{id}/ticket` | POST | Generar ticket de apuesta para el reto |

---

## 📁 Estructura del Proyecto

```
📦 nba-vibecoding/
├── 📄 main.py           # API FastAPI principal (PROCUCCIÓN)
├── 📄 prediction_api.py # Motor de predicciones XGBoost
├── 📄 history_db.py     # Gestión de historial y Cache
├── 📁 ladder/           # Módulo Project Phoenix (Escalera)
│   ├── main_ladder.py   # Orquestador de ciclos diarios
│   ├── strategy_engine.py # Lógica de bankroll y selección
│   └── groq_agent.py    # Agente de IA para tickets
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
