# Use Python 3.13 slim image
FROM python:3.13-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=yar_ff_django.settings

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        curl \
        netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy project
COPY . .

# Create logs directory BEFORE collectstatic (Django logging needs it)
RUN mkdir -p logs static

# Collect static files during build (no database needed for REST framework statics)
RUN python manage.py collectstatic --noinput --clear --verbosity=2

# Create non-root user
RUN addgroup --system django \
    && adduser --system --ingroup django django

# Set permissions for django user
RUN chown -R django:django /app

# Change to non-root user
USER django

# Health check (updated for new URL structure)
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Expose port
EXPOSE 8000

# Run the application
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "yar_ff_django.wsgi:application"]
