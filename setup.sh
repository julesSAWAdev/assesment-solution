#!/bin/bash
# Quick Setup Script for Crypto Data Pipeline

set -e  # Exit on error

echo "=================================================="
echo "  Crypto Data Pipeline - Setup"
echo "=================================================="
echo ""

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is not installed"
    echo "   Please install Docker from https://docs.docker.com/get-docker/"
    exit 1
fi

# Check Docker Compose (support both v1 and v2)
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Error: Docker Compose is not installed"
    echo "   Please install Docker Compose from https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✅ Docker and Docker Compose are installed"
echo ""

# Use docker compose if available, otherwise fallback to docker-compose
DOCKER_COMPOSE_CMD="docker compose"
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker-compose"
fi

# Build and start services
echo "🚀 Starting services..."
$DOCKER_COMPOSE_CMD up -d --build

echo ""
echo "⏳ Waiting for services to be healthy (this may take 30-60 seconds)..."
sleep 10

# Wait for PostgreSQL
echo "   Waiting for PostgreSQL..."
for i in {1..30}; do
    if docker exec crypto_postgres pg_isready -U pipeline_user -d crypto_data > /dev/null 2>&1; then
        echo "   ✅ PostgreSQL is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "   ❌ PostgreSQL failed to start"
        exit 1
    fi
    sleep 2
done

# Wait for Dagster
echo "   Waiting for Dagster..."
sleep 15
echo "   ✅ Dagster should be starting up"

echo ""
echo "=================================================="
echo "  ✅ Setup Complete!"
echo "=================================================="
echo ""
echo "Access Points:"
echo "  • Dagster UI:  http://localhost:3000"
echo "  • PostgreSQL:  localhost:5432"
echo "    - User: pipeline_user"
echo "    - Password: pipeline_pass"
echo "    - Database: crypto_data"
echo ""
echo "Next Steps:"
echo ""
echo "1. Run the complete pipeline:"
echo "   docker exec -it crypto_pipeline_runner python scripts/run_pipeline.py"
echo ""
echo "2. View data in PostgreSQL:"
echo "   docker exec -it crypto_postgres psql -U pipeline_user -d crypto_data"
echo ""
echo "3. Open Dagster UI:"
echo "   Open http://localhost:3000 in your browser"
echo ""
echo "4. View logs:"
echo "   $DOCKER_COMPOSE_CMD logs -f"
echo ""
echo "To stop: $DOCKER_COMPOSE_CMD down"
echo "To clean up everything: $DOCKER_COMPOSE_CMD down -v"
echo ""