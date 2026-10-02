#!/bin/bash
set -e

PYTHON=python3
ENV_DIR="$(pwd)/gpu_env"
ACTIVATE_SCRIPT="$ENV_DIR/bin/activate"
REQUIREMENTS_FILE="$(pwd)/requirements.txt"

if [ ! -f "$REQUIREMENTS_FILE" ]; then
    echo "ERROR: requirements.txt not found at $REQUIREMENTS_FILE"
    exit 1
fi

if [ -f "$ACTIVATE_SCRIPT" ]; then
    echo "Virtual environment found. Activating..."
    source "$ACTIVATE_SCRIPT"
else
    echo "Virtual environment not found. Creating in $ENV_DIR"
    $PYTHON -m venv "$ENV_DIR"

    echo "Activating virtual environment..."
    source "$ACTIVATE_SCRIPT"

    echo "Upgrading pip..."
    pip install --upgrade pip

    echo "Installing dependencies from requirements.txt..."
    pip install -r "$REQUIREMENTS_FILE"

    echo "Environment is ready."
fi

echo "To activate later, run:"
echo "source $ACTIVATE_SCRIPT"
