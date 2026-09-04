#!/bin/bash
# Personal Knowledge OS launcher (Linux).
# Run this (or double-click the .desktop icon that points to it) to start
# the backend + frontend and open the app in your browser. Closing this
# terminal window stops both servers.

# --- EDIT THIS if your project folder is somewhere else ---
PROJECT_DIR="$HOME/personal-knowledge-os"
BACKEND_PORT=8000
FRONTEND_PORT=5173
# ------------------------------------------------------------

cd "$PROJECT_DIR" || { echo "Could not find $PROJECT_DIR — edit PROJECT_DIR in this script."; read -r -p "Press Enter to close..."; exit 1; }

cleanup() {
  echo -e "\nShutting down..."
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null
  exit 0
}
trap cleanup EXIT INT TERM

# Free up the ports first, in case a previous run is still hanging around
# (this is very likely why Vite jumped to 5174 last time).
free_port() {
  local port=$1
  if command -v fuser > /dev/null; then
    fuser -k "${port}/tcp" 2>/dev/null
  elif command -v lsof > /dev/null; then
    lsof -ti tcp:"$port" | xargs -r kill -9
  fi
}
echo "Freeing ports $BACKEND_PORT and $FRONTEND_PORT if anything is still using them..."
free_port "$BACKEND_PORT"
free_port "$FRONTEND_PORT"
sleep 1

# --- Backend ---
echo "Starting backend..."
cd "$PROJECT_DIR/backend" || exit 1

VENV_DIR=""
for candidate in venv .venv env; do
  if [ -f "$candidate/bin/activate" ]; then
    VENV_DIR="$candidate"
    break
  fi
done

if [ -n "$VENV_DIR" ]; then
  echo "Using virtual environment: $VENV_DIR"
  source "$VENV_DIR/bin/activate"
else
  echo "WARNING: no venv/.venv/env folder found in backend/ — using system Python."
  echo "If uvicorn is 'not found' next, that's why. Create one with:"
  echo "  python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
fi

uvicorn app.main:app --port "$BACKEND_PORT" --reload > /tmp/pkos_backend.log 2>&1 &
BACKEND_PID=$!

echo "Waiting for the backend to come up..."
BACKEND_OK=0
for i in $(seq 1 20); do
  if curl -s "http://localhost:$BACKEND_PORT/api/health" > /dev/null 2>&1; then
    BACKEND_OK=1
    break
  fi
  sleep 1
done

if [ "$BACKEND_OK" -eq 0 ]; then
  echo ""
  echo "!!! Backend did not come up after 20 seconds. Last log lines:"
  tail -n 20 /tmp/pkos_backend.log
  echo ""
  echo "Full log: /tmp/pkos_backend.log"
  echo "Continuing anyway to start the frontend, but chat/study features won't work until this is fixed."
fi

# --- Frontend ---
echo "Starting frontend..."
cd "$PROJECT_DIR/frontend" || exit 1
# --strictPort makes Vite FAIL instead of silently picking a different port
# if $FRONTEND_PORT is already taken, so we never open the wrong URL again.
npm run dev -- --port "$FRONTEND_PORT" --strictPort > /tmp/pkos_frontend.log 2>&1 &
FRONTEND_PID=$!

echo "Waiting for the frontend to be ready..."
FRONTEND_OK=0
for i in $(seq 1 30); do
  if curl -s "http://localhost:$FRONTEND_PORT" > /dev/null 2>&1; then
    FRONTEND_OK=1
    break
  fi
  sleep 1
done

if [ "$FRONTEND_OK" -eq 0 ]; then
  echo ""
  echo "!!! Frontend did not come up after 30 seconds. Last log lines:"
  tail -n 20 /tmp/pkos_frontend.log
  echo ""
  echo "Full log: /tmp/pkos_frontend.log"
  echo "Not opening a browser since nothing is there yet."
else
  if command -v xdg-open > /dev/null; then
    xdg-open "http://localhost:$FRONTEND_PORT"
  else
    echo "Open this in your browser: http://localhost:$FRONTEND_PORT"
  fi
fi

echo -e "\nPersonal Knowledge OS is running (backend log: /tmp/pkos_backend.log, frontend log: /tmp/pkos_frontend.log)."
echo "Close this window (or press Ctrl+C) to stop it."

wait
