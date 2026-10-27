#!/usr/bin/env bash
# Create a macOS-only virtual environment for this project.
#
# This deliberately does not touch venv312/, which is the existing Windows
# environment. Run from the repository root:
#   bash scripts/setup_macos.sh
#   source .venv-macos/bin/activate

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PATH="$PROJECT_ROOT/.venv-macos"

# Python 3.12 has broadly available macOS wheels for the full ML stack
# (PyTorch, torchvision, scikit-learn). Do not use a just-released Python
# version unless every dependency explicitly supports it.
PYTHON_BIN=""
for candidate in python3.12 python3.13; do
    if command -v "$candidate" >/dev/null 2>&1; then
        PYTHON_BIN="$candidate"
        break
    fi
done

if [ -z "$PYTHON_BIN" ]; then
    echo "Python 3.12 or 3.13 is required. Install Python 3.12, then rerun this script."
    exit 1
fi

if [ ! -d "$VENV_PATH" ]; then
    "$PYTHON_BIN" -m venv "$VENV_PATH"
fi

"$VENV_PATH/bin/python" -m pip install --upgrade pip
"$VENV_PATH/bin/python" -m pip install -r "$PROJECT_ROOT/requirements.txt"

echo
echo "macOS environment is ready: $VENV_PATH"
echo "Activate it with: source .venv-macos/bin/activate"
