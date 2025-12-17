# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY results_requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r results_requirements.txt

# Copy application files
COPY results_app.py .
COPY results_models.py .
COPY results_database.py .
COPY templates/public templates/public/
COPY static/css/public.css static/css/

# Create directory for database
RUN mkdir -p /app/data

# Set environment variables
ENV PORT=8080
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8080

# Run with gunicorn
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 results_app:app
