# 🏀⚽ La Fija - Predicciones Deportivas Inteligentes

¡Bienvenido a **La Fija**! Este es un proyecto que utiliza Inteligencia Artificial (específicamente un tipo llamado Machine Learning) para intentar predecir los resultados de partidos deportivos de la **NBA** (Baloncesto) y **Fútbol Europeo**.

El sistema analiza datos y estadísticas históricas todos los días para darte la mejor "fija" (predicción) posible.

---

## 🎯 ¿Qué hace este proyecto exactamente?

Imagina un analista deportivo que no duerme. Eso es La Fija:
1. **Recopila datos:** Todos los días, el sistema busca los partidos que se jugarán hoy.
2. **Analiza estadísticas:** La IA mira cómo les ha ido a los equipos en el pasado.
3. **Lee las noticias (Solo NBA):** Gracias a otra Inteligencia Artificial llamada DeepSeek, el sistema también lee si hay jugadores lesionados importantes que puedan afectar el resultado.
4. **Te da el resultado:** La página web principal te muestra de forma muy clara quién cree el sistema que va a ganar.

## 📚 ¿Sin conocimientos técnicos? ¡No hay problema!

Hemos creado guías paso a paso, explicadas con peras y manzanas, para que cualquier persona pueda entender, instalar y jugar con este proyecto.

Empieza por aquí:

🔹 **[Guía de Inicio Rápido (Paso a Paso)](docs/GUIA_INICIO_RAPIDO.md)**
Aprende cómo descargar este código, preparar tu computadora y ver la página funcionando, ¡incluso si es tu primera vez!

🔹 **[Entendiendo los Servicios y APIs Externas](docs/SERVICIOS_Y_APIS.md)**
Aquí explicamos de forma sencilla todas esas palabras raras como "Render", "DeepSeek", "Supabase" o "Resend" y por qué las necesitamos.

---

## 🛠️ Para los más técnicos (Resumen Rápido)

Si ya sabes de programación, aquí tienes el resumen de lo que usamos bajo el capó:

- **Backend:** Python + FastAPI (súper ligero y rápido).
- **Inteligencia Artificial (Modelos):** XGBoost para NBA, Distribución de Poisson para Fútbol.
- **Frontend (La página web):** HTML, CSS y JavaScript clásicos (sin frameworks pesados).
- **Base de Datos Principal:** SQLite3 (para guardar el historial de predicciones sin complicaciones).
- **Automatización (CRON):** GitHub Actions ejecuta las predicciones todos los días a las 3:00 AM (Hora Colombia).
- **Despliegue Gratuito:** Todo está pensado para alojarse sin costo en servicios como **Render**.

### Estructura Principal del Código

```text
bet/
├── main.py                  # El cerebro de la página web (FastAPI)
├── prediction_api.py        # La IA que predice la NBA
├── football_api.py          # La IA que predice el Fútbol
├── history_db.py            # Archivo que guarda las cosas en la base de datos
├── generate_daily_job.py    # El script que se ejecuta todos los días a las 3 AM
├── docs/                    # Todas las guías y documentación detallada
├── static/                  # La carpeta donde vive el diseño de la web
```

---

*¡Gracias por echarle un vistazo a La Fija! Si tienes problemas durante la instalación, consulta nuestra [Guía de Inicio Rápido](docs/GUIA_INICIO_RAPIDO.md).*
