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
| `GET /admin` | Panel de administración |
| `GET /api/settings` | Configuración pública (tema, publicidad) |
| `POST /api/admin/login` | Login admin (JWT) |
| `GET/POST /api/admin/settings` | Configuración (requiere JWT) |

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
# Panel admin: http://localhost:8080/admin
```

**Panel de administración:** En el primer despliegue (sin `admin_settings.json`) se usa la configuración por defecto. Contraseña inicial: **`LaFijaAdmin2025!`** — cámbiala en Admin → Seguridad al entrar.
Para configurar la contraseña en local: `python admin_config.py set-password`

**Recuperar contraseña por correo:** En la pantalla de login, "¿Olvidaste tu contraseña?" envía un enlace al correo del administrador.

- **Render Free:** El plan gratuito de Render **bloquea los puertos SMTP** (25, 465, 587), así que Gmail/Outlook SMTP no funcionan. Usa **Resend** (API HTTP, gratis ~100 emails/día):
  1. Regístrate en [resend.com](https://resend.com) y crea una API Key en [resend.com/api-keys](https://resend.com/api-keys).
  2. En Render → tu servicio → **Environment** añade:
     - `ADMIN_RECOVERY_EMAIL`: tu correo (ej. `hasler9710@gmail.com`).
     - `RESEND_API_KEY`: la API key de Resend (empieza por `re_`).
     - `RESEND_FROM`: remitente, ej. `La Fija <onboarding@resend.dev>` (o un dominio verificado en Resend).
     - `RENDER_EXTERNAL_URL` o `SITE_URL`: URL de tu sitio (ej. `https://tu-app.onrender.com`).
  3. Guarda y redeploya. La recuperación usará la API de Resend en lugar de SMTP.
- **Servidor con SMTP (VPS, Render paid, etc.):** Opcionalmente configura `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`. Si además existe `RESEND_API_KEY`, se prioriza Resend.

**Verificar historial (pendientes antes del 03/03/2026):**
```bash
python scripts/verify_history_db.py          # listar pendientes
python scripts/verify_history_db.py --fix    # actualizar marcadores
```
