#!/usr/bin/env pwsh
<#
.SYNOPSIS
    EcoSort AI - Quick Start Script (Windows PowerShell)
.DESCRIPTION
    Starts both the frontend (React/Vite) and backend (FastAPI) servers.
    Assumes dependencies are already installed.
    Run from the ecosort-ai/ root directory.
#>

Write-Host "🌿 EcoSort AI - Starting development servers..." -ForegroundColor Green
Write-Host ""

# Check if frontend node_modules exists
if (-not (Test-Path "frontend\node_modules")) {
    Write-Host "📦 Installing frontend dependencies..." -ForegroundColor Yellow
    Set-Location frontend
    npm install
    Set-Location ..
}

# Check if backend venv exists
if (-not (Test-Path "backend\venv")) {
    Write-Host "🐍 Creating Python virtual environment..." -ForegroundColor Yellow
    Set-Location backend
    python -m venv venv
    .\venv\Scripts\pip install -r requirements.txt
    Set-Location ..
}

Write-Host "🔧 Starting FastAPI backend on http://localhost:8000 ..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD\backend'; .\venv\Scripts\activate; python run.py"

Start-Sleep -Seconds 2

Write-Host "⚛️  Starting React frontend on http://localhost:5173 ..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD\frontend'; npm run dev"

Write-Host ""
Write-Host "✅ Both servers are starting. Open http://localhost:5173 in your browser." -ForegroundColor Green
Write-Host "   Backend API docs: http://localhost:8000/docs" -ForegroundColor Gray
Write-Host ""
Write-Host "⚠️  To use demo mode without the backend, set VITE_DEMO_MODE=true in frontend/.env" -ForegroundColor Yellow
