# 🏀 NBA Predictor AI

> **Motor híbrido de predicciones NBA:** Combina XGBoost (análisis numérico) con Groq LLM (análisis inteligente) para predicciones de alta calidad.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green?logo=fastapi)
![XGBoost](https://img.shields.io/badge/XGBoost-2.0+-orange)
![Groq](https://img.shields.io/badge/Groq-Llama_3.3_70B-purple)

---

## 📋 Descripción

Este proyecto utiliza un enfoque de **IA híbrida** para predecir resultados de la NBA:

1. **Motor Numérico (XGBoost):** Modelos entrenados con ~69% de efectividad que analizan estadísticas históricas.
2. **Motor Inteligente (Groq LLM):** Llama 3.3 70B genera análisis detallados explicando el "por qué" de cada recomendación.
3. **Carga Ultrarrápida:** Optimización con memoria persistente (SQLite) para cargar resultados en menos de 500ms.

---

## 🚀 Instalación Local

### 1. Clonar el repositorio
```bash
git clone https://github.com/ApkVox/bet.git
cd bet
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

## 📡 Funciones Principales

| Función | Método | Descripción |
|----------|--------|-------------|
| `/predict-today` | GET | Predicciones del día (con IA) |
| `/history/full` | GET | Historial detallado de aciertos |
| `/history` | GET | Historial resumido |
| `/update-history` | POST | Sincroniza resultados reales |

---

## 📁 Estructura del Proyecto

```
📦 nba-predictor-ai/
├── 📄 main.py           # API principal (FastAPI)
├── 📄 prediction_api.py # Motor de IA XGBoost
├── 📄 history_db.py     # Base de datos e historial
├── 📁 static/           # Panel de Control (Frontend)
├── 📁 Data/             # Almacenamiento
│   ├── history.db       # Historial de aciertos
│   └── TeamData.sqlite  # Base de datos de equipos
└── 📁 Models/           # Modelos de inteligencia artificial
```

---

## ⚙️ Tecnologías Usadas

| Componente | Tecnología |
|------------|------------|
| Backend | FastAPI |
| Motor de IA | XGBoost + Scikit-learn |
| Analista IA | Groq API (Llama 3.3 70B) |
| Datos | SQLite + Pandas |
| Panel | HTML5 + CSS3 + JS (Vainilla) |

---

## 📝 Nota Legal

Este proyecto es para fines educativos y de entretenimiento. Las predicciones NO garantizan ganancias y no deben usarse para apuestas reales. Juéguelo con responsabilidad.

---

<p align="center">
  <strong>Hecho con ❤️ y Machine Learning</strong>
</p>
