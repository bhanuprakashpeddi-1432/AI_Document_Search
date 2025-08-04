@echo off
REM HackRX Development Setup Script for Windows
REM This script sets up the development environment

echo 🚀 Setting up HackRX Development Environment

REM Check if Docker is installed
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker is not installed. Please install Docker Desktop first.
    exit /b 1
)

REM Check if Docker Compose is installed
docker-compose --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker Compose is not installed. Please install Docker Compose first.
    exit /b 1
)

REM Create .env file if it doesn't exist
if not exist .env (
    echo 📝 Creating .env file from template...
    copy .env.example .env
    echo ⚠️  Please edit .env file with your API keys before running the application
)

REM Build and start services
echo 🏗️  Building and starting services...
docker-compose build

echo 🔍 Starting PostgreSQL...
docker-compose up -d postgres

echo ⏳ Waiting for PostgreSQL to be ready...
timeout /t 10 /nobreak

echo 🚀 Starting all services...
docker-compose up -d

echo ✅ Setup complete!
echo.
echo 🌐 Application URLs:
echo    Frontend: http://localhost:3000
echo    Backend:  http://localhost:8000
echo    API Docs: http://localhost:8000/docs
echo.
echo 📋 Next steps:
echo    1. Edit .env file with your API keys
echo    2. Run: docker-compose restart
echo    3. Open http://localhost:3000 in your browser
echo.
echo 🔧 Useful commands:
echo    View logs:    docker-compose logs -f
echo    Stop:         docker-compose down
echo    Rebuild:      docker-compose build --no-cache

pause
