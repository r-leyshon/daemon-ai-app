#!/bin/bash
echo "Starting Daemon AI Backend..."
echo "Current directory: $(pwd)"
echo "Python version: $(python --version)"
echo "Pip version: $(pip --version)"
echo "Listing files:"
ls -la

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Starting gunicorn..."
cd /home/site/wwwroot
gunicorn --bind=0.0.0.0 --timeout 600 main:app 