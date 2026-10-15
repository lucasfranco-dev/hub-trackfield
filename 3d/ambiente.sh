# Configuração comum aos scripts de render (use com: . 3d/ambiente.sh).
# Acha o Python do venv no Linux/Mac (.venv-blender/bin/python) e no Windows
# (.venv-blender/Scripts/python.exe); PYTHON_BLENDER, se definido, tem prioridade.
if [ -z "${PYTHON_BLENDER:-}" ]; then
  if [ -x .venv-blender/bin/python ]; then
    PYTHON_BLENDER=.venv-blender/bin/python
  elif [ -x .venv-blender/Scripts/python.exe ]; then
    PYTHON_BLENDER=.venv-blender/Scripts/python.exe
  else
    echo "Não achei o Python do Blender. Crie o venv (veja o README) ou defina PYTHON_BLENDER." >&2
    exit 1
  fi
fi
PY="$PYTHON_BLENDER"
export DISPOSITIVO="${DISPOSITIVO:-CPU}"
