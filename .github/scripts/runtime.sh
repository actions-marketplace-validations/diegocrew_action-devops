#!/usr/bin/env bash
# Shared path and virtualenv handling; optional PYTHON_EXECUTABLE selects tooling Python.
if [[ "${RUNNER_OS:-}" == Windows ]]; then
  RUNNER_TEMP=$(cygpath -u "$RUNNER_TEMP")
fi

create_python_env() {
  local directory="$1"
  "${PYTHON_EXECUTABLE:-python}" -m venv "$directory"
  if [[ "${RUNNER_OS:-}" == Windows ]]; then
    VENV_BIN="$directory/Scripts"
    VENV_PYTHON="$VENV_BIN/python.exe"
  else
    VENV_BIN="$directory/bin"
    VENV_PYTHON="$VENV_BIN/python"
  fi
  export VENV_BIN VENV_PYTHON
}
