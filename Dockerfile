FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . /app

# Run migrations and collect static files
RUN python manage.py migrate --noinput || true
RUN python manage.py collectstatic --noinput || true

# Create necessary directories
RUN mkdir -p /app/tmp_uploads /app/staticfiles

EXPOSE $PORT

CMD python manage.py migrate --noinput && \
    gunicorn portal.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120

