#!/bin/bash

# Integration Test Runner for Order Processing System
# This script starts Docker services, seeds data, runs integration tests, and cleans up

set -e  # Exit on error

echo "=========================================="
echo "Integration Test Runner"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Cleanup function
cleanup() {
    print_status "Cleaning up..."
    docker compose down -v
    rm -rf venv_tests
    print_status "Cleanup complete"
}

# Set trap to cleanup on exit
trap cleanup EXIT

# Step 1: Stop any existing services
print_status "Stopping any existing services..."
docker compose down -v

# Step 2: Build services
print_status "Building Docker services..."
docker compose build

# Step 3: Start services
print_status "Starting Docker services..."
docker compose up -d

# Step 4: Wait for services to be healthy
print_status "Waiting for services to be healthy..."
echo "This may take 30-60 seconds..."

# Wait for databases
print_status "Waiting for databases..."
sleep 10

# Check if order-service is responding
MAX_RETRIES=30
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s http://localhost:8000/docs > /dev/null 2>&1; then
        print_status "Order service is ready!"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "Waiting for order service... ($RETRY_COUNT/$MAX_RETRIES)"
    sleep 2
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    print_error "Order service failed to start"
    docker compose logs order-service
    exit 1
fi

# Additional wait for event processing to be ready
print_status "Waiting for all services to stabilize..."
sleep 10

# Step 5: Seed inventory data
print_status "Seeding inventory data..."
docker compose exec -T inventory-service python app/seeder.py || {
    print_warning "Seeder script not found or failed, continuing anyway..."
}

# Step 6: Show service status
print_status "Service status:"
docker compose ps

# Step 7: Install test dependencies
print_status "Installing test dependencies..."
# We are already in the project root, dependencies are managed by poetry in each service.
# For integration tests, we need some common libs. They should be in the root pyproject or we install them in a temp env.
# Since we are using poetry in services, let's use the local python environment if available, or just skip if packages are present.
# Ideally, we should have a root pyproject.toml for integration tests.
# For now, let's assume requirements.txt has what we need and user has python/pip or poetry.

# Try using poetry if available and a pyproject.toml exists in tests/ (which it doesn't seem to).
# Instead, let's just make sure we have the deps.
# Since the user environment seems to have poetry, let's use poetry run pip if we are in a poetry env,
# or just assume the user has the test deps installed in their environment.

# Better approach: Create a temporary virtualenv for tests
python3 -m venv venv_tests
source venv_tests/bin/activate
pip install -q -r tests/requirements.txt || {
    print_error "Failed to install test dependencies"
    exit 1
}

# Step 8: Run integration tests
print_status "Running integration tests..."
echo ""
echo "=========================================="
echo "INTEGRATION TEST RESULTS"
echo "=========================================="
echo ""

cd tests
../venv_tests/bin/pytest test_integration.py -v --tb=short --color=yes || {
    TEST_EXIT_CODE=$?
    print_error "Integration tests failed with exit code $TEST_EXIT_CODE"
    echo ""
    print_status "Showing service logs for debugging..."
    echo ""
    docker compose logs --tail=50
    exit $TEST_EXIT_CODE
}
cd ..

echo ""
print_status "✅ All integration tests passed!"
echo ""

# Step 9: Show final service status
print_status "Final service status:"
docker compose ps

echo ""
print_status "Integration tests completed successfully!"
echo ""
