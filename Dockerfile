FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Temporary SECRET_KEY for build so collectstatic does not fail
ENV SECRET_KEY=dummysecretkeyfordockerbuild

# Collect static files at build time
RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate && gunicorn krishiSathi.wsgi:application --bind 0.0.0.0:8000"]

