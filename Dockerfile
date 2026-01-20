# ===========================================
# NBA VIBECODING PREDICTOR - DOCKERFILE
# Optimizado para Render (Python 3.10 Slim)
# ===========================================

FROM python:3.10-slim

# Evitar prompts interactivos
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instalar dependencias de sistema para compilar numpy/xgboost
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Directorio de trabajo
WORKDIR /app

# Copiar e instalar dependencias primero (mejor cache de Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copiar TODO el proyecto (incluye src/, Data/, Models/)
COPY . .

# Puerto de Render
EXPOSE 10000

# Comando de inicio
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
