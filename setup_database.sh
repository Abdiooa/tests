#!/bin/bash
# Database setup script for Telecom XDR Records API

set -e

echo "========================================="
echo "Telecom XDR Records - Database Setup"
echo "========================================="
echo ""

# Database configuration
DB_NAME="test_db"
DB_USER="postgres"
DB_PASSWORD="dadinos"
DB_HOST="localhost"
DB_PORT="5432"

echo "Database Configuration:"
echo "  Database: $DB_NAME"
echo "  Host: $DB_HOST:$DB_PORT"
echo "  User: $DB_USER"
echo ""

# Check if PostgreSQL is running
echo "Checking PostgreSQL status..."
if ! systemctl is-active --quiet postgresql 2>/dev/null; then
    echo "Warning: PostgreSQL service doesn't appear to be running."
    echo "Please start PostgreSQL manually:"
    echo "  sudo systemctl start postgresql"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo "✓ PostgreSQL is running"
fi

# Check if database exists
echo ""
echo "Checking if database exists..."
if PGPASSWORD=$DB_PASSWORD psql -U $DB_USER -h $DB_HOST -lqt | cut -d \| -f 1 | grep -qw $DB_NAME; then
    echo "✓ Database '$DB_NAME' already exists"
else
    echo "Creating database '$DB_NAME'..."
    PGPASSWORD=$DB_PASSWORD createdb -U $DB_USER -h $DB_HOST $DB_NAME
    echo "✓ Database created successfully"
fi

# Test database connection
echo ""
echo "Testing database connection..."
if PGPASSWORD=$DB_PASSWORD psql -U $DB_USER -h $DB_HOST -d $DB_NAME -c "SELECT 1;" > /dev/null 2>&1; then
    echo "✓ Database connection successful"
else
    echo "✗ Failed to connect to database"
    echo "Please check your PostgreSQL configuration and credentials"
    exit 1
fi

# Initialize tables
echo ""
echo "Initializing database tables (with cleanup)..."
echo "⚠️  This will DROP all existing tables and data!"
if [ -f "init_db.py" ]; then
    # Try to use virtual environment Python first
    if [ -f "venv/bin/python" ]; then
        echo "Using virtual environment Python..."
        ./venv/bin/python init_db.py
    elif [ -f "venv/bin/python3" ]; then
        echo "Using virtual environment Python..."
        ./venv/bin/python3 init_db.py
    elif command -v python3 &> /dev/null; then
        echo "Warning: Using system Python (virtual environment not found)"
        python3 init_db.py
    else
        echo "Warning: Python3 not found. Please run 'python init_db.py' manually"
    fi
else
    echo "Warning: init_db.py not found. Tables will be created automatically when the app starts."
fi

echo ""
echo "========================================="
echo "Database setup complete!"
echo "========================================="
echo ""
echo "You can now start the API server:"
echo "  python app.py"
echo ""
echo "Or with uvicorn:"
echo "  uvicorn app:app --reload --host 0.0.0.0 --port 8000"
echo ""

