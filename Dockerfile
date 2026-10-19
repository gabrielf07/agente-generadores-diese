# Usa una imagen oficial de Python ligera
FROM python:3.11-slim

# Define el directorio de trabajo dentro del contenedor
WORKDIR /app

# Instala dependencias del sistema operativo que algunas librerías de Python pueden necesitar
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copia el archivo de requerimientos primero para aprovechar la caché de Docker
COPY requirements.txt .

# Instala las librerías de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo el resto de los archivos de tu proyecto al contenedor
# (Esto incluirá app.py, agent.py, la carpeta chroma_db, bm25_docs.pkl y el .env)
COPY . .

# Expone el puerto por defecto (8501 localmente)
EXPOSE 8501

# Comando para ejecutar la aplicación web adaptándose al puerto dinámico de Render o al 8501 por defecto
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8501}"]