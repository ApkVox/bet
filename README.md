# 🏀 NBA Predictor AI

> **Tu Analista Deportivo Inteligente:** Un sistema avanzado que fusiona Machine Learning con Inteligencia Artificial Generativa para ofrecer predicciones de la NBA con profundidad táctica y precisión estadística.

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![XGBoost](https://img.shields.io/badge/XGBoost-2.0+-FF6B6B?style=for-the-badge&logo=xgboost&logoColor=white)
![Groq](https://img.shields.io/badge/Groq-Llama_3_70B-f55036?style=for-the-badge&logo=meta&logoColor=white)
![Status](https://img.shields.io/badge/Estado-Activo-success?style=for-the-badge)

---

## 📖 Tabla de Contenidos

- [Descripción General](#-descripción-general)
- [Características Principales](#-características-principales)
- [Arquitectura del Sistema](#-arquitectura-del-sistema)
- [Instalación y Configuración](#-instalación-y-configuración)
- [Uso de la Aplicación](#-uso-de-la-aplicación)
- [API Reference](#-api-reference)
- [Stack Tecnológico](#-stack-tecnológico)
- [Licencia](#-licencia)

---

## 📋 Descripción General

**NBA Predictor AI** no es solo otro modelo de predicción. Es un ecosistema completo que resuelve el problema de la "caja negra" en las apuestas deportivas. Mientras que los modelos tradicionales solo te dan un número (ej. "Lakers 60%"), nuestro sistema te explica el **POR QUÉ**.

Utilizamos un enfoque híbrido:
1.  **Cerebro Numérico (XGBoost):** Analiza miles de puntos de datos históricos (eficiencia ofensiva, ritmo, rebotes, historial de enfrentamientos) para calcular probabilidades matemáticas puras.
2.  **Cerebro Analítico (Llama 3.3 vía Groq):** Actúa como un experto comentarista deportivo, analizando factores cualitativos como lesiones de último minuto, narrativas de "revancha", fatiga por viajes y dinámica de vestuario.

---

## ✨ Características Principales

### 🧠 Predicciones Híbridas
Combina la precisión de los datos duros con la intuición del análisis de texto. El modelo numérico sugiere **quién** ganará, y la IA explica **cómo** y **por qué**.

### 📊 Dashboard Interactivo (SPA)
Una interfaz moderna y responsiva construida con Vanilla JS para máxima velocidad.
- **Vista de Predicciones:** Tarjetas detalladas con probabilidades, cuotas estimadas y análisis.
- **Modo Oscuro:** Diseño "Glassmorphism" elegante y cómodo para la vista.
- **Responsive:** Funciona perfectamente en móviles, tablets y escritorio.

### 💰 Gestión de Bankroll (Criterio de Kelly)
No solo te dice a quién apostar, sino **cuánto**. El sistema calcula el "Valor Esperado" (EV) y sugiere el tamaño de la apuesta óptimo basado en tu ventaja matemática, protegiendo tu capital.

### ⚡ Rendimiento Extremo
- **Cache Inteligente (SQLite):** Los resultados se guardan para evitar recálculos, ofreciendo tiempos de carga instantáneos (<500ms).
- **Actualización en Tiempo Real:** Sistema capaz de refrescar datos y ajustar predicciones según nueva información.

### 📱 Diseño "Mobile-First"
Interfaz optimizada para dedos, con navegación inferior en móviles, tablas con scroll horizontal y modales adaptables.

---

## 🏗 Arquitectura del Sistema

El flujo de decisión sigue estos pasos rigurosos:

1.  **Ingesta de Datos:** Recopilación de estadísticas de `TeamData.sqlite` y cuotas de mercado.
2.  **Feature Engineering:** Cálculo de métricas avanzadas (Elo, Home Advantage, Rest Days).
3.  **Inferencia ML:** El modelo XGBoost genera la probabilidad base.
4.  **Contextualización IA:** Se envía un prompt estructurado a Groq (Llama 3.3) con los datos del partido + contexto de lesiones.
5.  **Síntesis:** La API combina ambos resultados y los sirve al Frontend.

---

## 🚀 Instalación y Configuración

Sigue estos pasos para desplegar tu propio oráculo de la NBA.

### Prerrequisitos
- Python 3.10 o superior
- Git

### Paso 1: Clonar el Repositorio
```bash
git clone https://github.com/ApkVox/bet.git
cd bet
```

### Paso 2: Crear Entorno Virtual
Es crucial aislar las dependencias.
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# Mac/Linux
python3 -m venv venv
source venv/bin/activate
```

### Paso 3: Instalar Dependencias
```bash
pip install -r requirements.txt
```

### Paso 4: Configurar Variables de Entorno
Necesitas una API Key de Groq (es gratuita actualmente).
1. Crea un archivo `.env` en la raíz.
2. Añade tu clave:
```env
GROQ_API_KEY=gsk_tu_clave_secreta_aqui
PORT=8000
```

### Paso 5: Ejecutar el Servidor
```bash
python main.py
```
Visita `http://localhost:8000` en tu navegador.

---

## 🎮 Uso de la Aplicación

1.  **Inicio:** Al abrir la app, verás los partidos de hoy automáticamente.
2.  **Ver Análisis:** Haz clic en "Más Datos" en cualquier partido para abrir el modal con el desglose de la IA.
3.  **Filtrar:** Usa el filtro "Solo mejores oportunidades (Valor+)" para ver solo las apuestas matemáticamente rentables.
4.  **Historial:** Navega a la pestaña "Historial" para ver el rendimiento pasado del modelo (Ganados/Perdidos y Balance).

---

## 📡 API Reference

La API está documentada automáticamente. Visita `/docs` para ver Swagger UI.

### Endpoints Clave

| Método | Endpoint | Descripción |
|:---:|:---|:---|
| `GET` | `/predict-today` | Obtiene predicciones para los juegos de hoy. |
| `GET` | `/history/full` | Historial completo de predicciones y resultados. |
| `GET` | `/match-details/{home}/{away}` | Detalles profundos y análisis específico de un cruce. |
| `POST` | `/update-history` | Trigger manual para actualizar resultados de juegos terminados. |

---

## 🛠 Stack Tecnológico

- **Backend:** Python, FastAPI, Uvicorn.
- **Machine Learning:** XGBoost, Scikit-Learn, Pandas, NumPy.
- **Inteligencia Artificial:** Groq Cloud API (Llama 3.3 70B Versatile).
- **Base de Datos:** SQLite (ligera, rápida y sin configuración).
- **Frontend:** HTML5, Tailwind CSS (vía CDN), Vanilla JavaScript.
- **Despliegue:** Docker Ready.

---

## 📝 Licencia

Este proyecto se distribuye bajo la licencia MIT. Siéntete libre de usarlo, modificarlo y compartirlo.

> **⚠️ AVISO DE RESPONSABILIDAD:** Esta herramienta es para fines educativos y de entretenimiento. Las predicciones deportivas conllevan riesgos financieros. No apuestes dinero que no puedas permitirte perder.

---

<div align="center">
  <h3>Hecho con ❤️, Código y Baloncesto 🏀</h3>
  <p>Desarrollado por el equipo de NBA Predictor AI</p>
</div>
