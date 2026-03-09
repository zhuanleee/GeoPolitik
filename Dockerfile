FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ .

# Create data directory (Render disk mounts here)
RUN mkdir -p /data/geopol

EXPOSE 10000

# Render uses port 10000 by default
CMD ["uvicorn", "geopol_api:app", "--host", "0.0.0.0", "--port", "10000"]
