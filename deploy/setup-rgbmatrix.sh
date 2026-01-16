#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-$HOME/rgbmatrix-stack}"
VENV_NAME="${VENV_NAME:-.venv}"
REPO_URL="${REPO_URL:-https://github.com/hzeller/rpi-rgb-led-matrix.git}"
REPO_BRANCH="${REPO_BRANCH:-master}"
SETCAP="${SETCAP:-1}"   # DEFAULT ON

echo "[1/9] Installing dependencies (apt)..."
sudo apt-get update
sudo apt-get install -y \
  git \
  build-essential \
  g++ \
  make \
  pkg-config \
  cython3 \
  python3 \
  python3-venv \
  python3-dev \
  libcap2-bin \
  ca-certificates \
  curl

# inside root
make
make install-python

# inside bindings/python

echo "[2/9] Creating install dir: $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

if [[ -d "rpi-rgb-led-matrix/.git" ]]; then
  echo "[3/9] Updating existing repo..."
  ( cd rpi-rgb-led-matrix && \
    git fetch --all --prune && \
    git checkout "$REPO_BRANCH" && \
    git pull )
else
  echo "[3/9] Cloning repo..."
  git clone --branch "$REPO_BRANCH" --depth 1 "$REPO_URL" rpi-rgb-led-matrix
fi

# echo "[4/9] Verifying expected source files exist..."
# BIND_DIR="$INSTALL_DIR/rpi-rgb-led-matrix/bindings/python"
# if [[ ! -d "$BIND_DIR" ]]; then
#   echo "ERROR: bindings/python directory not found at: $BIND_DIR" >&2
#   exit 1
# fi

# if [[ ! -f "$BIND_DIR/rgbmatrix/core.cpp" ]]; then
#   echo "ERROR: Expected file missing: $BIND_DIR/rgbmatrix/core.cpp" >&2
#   echo "This usually means you're not in hzeller's repo checkout, or the checkout is incomplete." >&2
#   echo "Contents of $BIND_DIR:" >&2
#   ls -la "$BIND_DIR" >&2 || true
#   echo "Contents of $BIND_DIR/rgbmatrix:" >&2
#   ls -la "$BIND_DIR/rgbmatrix" >&2 || true
#   exit 1
# fi

echo "[5/9] Creating Python venv: $INSTALL_DIR/$VENV_NAME"
python3 -m venv "$VENV_NAME"
# shellcheck disable=SC1091
source "$VENV_NAME/bin/activate"

echo "[6/9] Upgrading pip tooling..."
python -m pip install -U pip setuptools wheel

echo "[7/9] Building + installing Python bindings into venv..."
cd "$BIND_DIR"
rm -rf build dist *.egg-info

# Editable install is reliable for this repo layout.
python -m pip install -v -e .

echo "[8/9] Verifying import..."
python - <<'PY'
import sys
print("Python:", sys.executable)
import rgbmatrix
print("rgbmatrix imported from:", rgbmatrix.__file__)
import rgbmatrix.core
print("rgbmatrix.core: OK")
PY

cd "$INSTALL_DIR"

if [[ "$SETCAP" == "1" ]]; then
  echo "[9/9] Setting capability so venv python can access /dev/mem without sudo..."
  VENV_PY="$(readlink -f "$INSTALL_DIR/$VENV_NAME/bin/python")"
  sudo setcap cap_sys_rawio+ep "$VENV_PY"
  echo "Capability set on: $VENV_PY"
else
  echo "[9/9] Skipping setcap (SETCAP=0). You may need sudo to access the matrix."
fi

cat <<EOF

Done.

Repo:
  $INSTALL_DIR/rpi-rgb-led-matrix

Virtualenv:
  source "$INSTALL_DIR/$VENV_NAME/bin/activate"

Quick test (NO sudo):
  python -c "import rgbmatrix; import rgbmatrix.core; print('OK')"

EOF
