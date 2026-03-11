@echo off
echo Drone Swarm Qdrant Manager (Using Existing Container)
echo =================================================

if "%1"=="" (
    echo Usage: manage_qdrant.bat [command]
    echo.
    echo Commands:
    echo   status     - Check container status
    echo   create     - Create drone_swarm_faces collection
    echo   test       - Test connection
    echo   stats      - Show collection statistics
    echo   list       - List all collections
    echo   start      - Start container if stopped
    echo   stop       - Stop container
    goto :eof
)

if "%1"=="status" (
    echo Checking Qdrant container status...
    docker ps --filter "name=qdrant"
    echo.
    echo Testing API connection...
    curl -s http://localhost:6333/healthz
    if %errorlevel% equ 0 (
        echo ✅ Qdrant is running
    ) else (
        echo ❌ Qdrant is not responding
    )
    goto :eof
)

if "%1"=="create" (
    echo Creating drone_swarm_faces collection...
    python scripts/create_drone_collection.py
    goto :eof
)

if "%1"=="test" (
    echo Testing connection...
    python tests/test_connection.py
    goto :eof
)

if "%1"=="list" (
    echo Listing all collections...
    curl -s http://localhost:6333/collections
    goto :eof
)

if "%1"=="stats" (
    echo Getting collection stats...
    python -c "from vision.qdrant_client import DroneQdrantClient; client=DroneQdrantClient(); print(client.get_statistics())"
    goto :eof
)

if "%1"=="start" (
    echo Starting Qdrant container...
    docker start qdrant
    goto :eof
)

if "%1"=="stop" (
    echo Stopping Qdrant container...
    docker stop qdrant
    goto :eof
)

echo Unknown command: %1