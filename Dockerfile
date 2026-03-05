# ---- Build Stage ----
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies required by psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
 && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY backend/ .

# Expose the port Render will map to
EXPOSE 8000

# Start the FastAPI app with uvicorn
# Render sets the PORT environment variable; default to 8000
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]

