@echo off
title IoT Transformer Health AI SCADA
echo ======================================================================
echo   IoT Transformer Health Prediction System (Software Suite)
echo   Layers 1 to 5: Synthetic Data -> MQTT -> HiveMQ -> SQLite -> ML -> Web App
echo ======================================================================
echo.

python run_project.py --component all

pause
