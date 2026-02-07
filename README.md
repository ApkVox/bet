# 🏀 NBA Predictor AI

> **Tu Analista Deportivo Inteligente** — Predicciones NBA con Machine Learning e Inteligencia Artificial

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![XGBoost](https://img.shields.io/badge/XGBoost-2.0+-FF6B6B?style=for-the-badge&logo=xgboost&logoColor=white)

---

## ✨ Características

| Característica | Descripción |
|:---|:---|
| 🎯 **Predicciones ML** | Modelo XGBoost con 68.9% de precisión |
| 🌓 **Modo Oscuro/Claro** | Toggle de tema con auto-detect del sistema |
| 📱 **Diseño Responsive** | Optimizado para móviles (Bento Grid estilo Apple) |
| 📊 **Dashboard Interactivo** | Stats en tiempo real con diseño glassmorphism |
| 📜 **Historial Completo** | Tracking de WIN/LOSS con filtros |

---

## 🎨 Diseño

El frontend utiliza un diseño inspirado en **Apple Bento Grid**:

- **Tarjetas con esquinas redondeadas** (border-radius: 24px)
- **Sombras suaves** para profundidad
- **Paleta de colores minimalista** (grises + azul acento)
- **Animaciones sutiles** en hover y transiciones
- **Navegación bottom** en dispositivos móviles

### Temas

| Light Mode | Dark Mode |
|:---:|:---:|
| `#f5f5f7` background | `#000000` background |
| `#ffffff` cards | `#1c1c1e` cards |
| `#0071e3` accent | `#0a84ff` accent |

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
echo "GROQ_API_KEY=tu_api_key" > .env

# Ejecutar
python main.py
```

Visita `http://localhost:8000`

---

## 📡 API

| Método | Endpoint | Descripción |
|:---:|:---|:---|
| `GET` | `/predict-today` | Predicciones del día |
| `GET` | `/history/full` | Historial completo |
| `GET` | `/api/update-pending` | Sincronizar resultados |

Documentación Swagger: `/docs`

---

## 📂 Estructura

```
bet/
├── main.py              # API FastAPI
├── prediction_api.py    # Motor XGBoost
├── history_db.py        # Persistencia SQLite
├── static/index.html    # Frontend (Bento Grid)
├── Data/                # Bases de datos
└── Models/              # Modelos entrenados
```

---

## 🌐 Despliegue

**Producción:** https://bet-7b8l.onrender.com

```bash
docker build -t nba-predictor .
docker run -p 8000:8000 --env-file .env nba-predictor
```

---

> ⚠️ **AVISO:** Herramienta educativa. Las predicciones deportivas conllevan riesgos. No apuestes dinero que no puedas perder.

<div align="center">
  <sub>Hecho con ❤️ y 🏀</sub>
</div>
