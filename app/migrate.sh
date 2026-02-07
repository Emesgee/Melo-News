#!/bin/bash

# Wait for database to be ready
echo "Waiting for database to be ready..."
until docker-compose exec db pg_isready -U user -d mydb; do
  echo "Database is unavailable - sleeping"
  sleep 2
done

echo "Database is ready!"
echo "Running database migrations..."

# Run migrations (example with Flask-Migrate)
docker-compose exec backend flask db upgrade

echo "Database migrations completed!"
