# ===========================================
# NBA PREDICTOR AI - DOCKERFILE
# Optimizado para Render (Python 3.10 Slim)
# ===========================================

FROM python:3.11-slim

# Evitar prompts interactivos
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV MALLOC_TRIM_THRESHOLD_=100000

# Instalar dependencias de sistema para compilar numpy/xgboost
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# ===========================================
# SECURITY: Crear usuario no-root (UID 1000 requerido por HF)
# ===========================================
RUN useradd -m -u 1000 appuser

# Directorio de trabajo
WORKDIR /app

# Copiar e instalar dependencias primero (mejor cache de Docker)
COPY requirements_prod.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements_prod.txt

# Copiar TODO el proyecto (incluye src/, Data/, Models/)
COPY . .

# Cambiar ownership al usuario no-root
RUN chown -R appuser:appuser /app

# Cambiar a usuario no-root
USER appuser

# Puerto estándar de Hugging Face Spaces
EXPOSE 7860

# Comando de inicio
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1"]
