
set -e
VENV=/opt/AI-PM/backend/venv
PIP="$VENV/bin/python -m pip"
export HUGGINGFACE_HUB_CACHE=/opt/AI-PM/.cache/huggingface
export HF_HOME=/opt/AI-PM/.cache/huggingface
mkdir -p $HUGGINGFACE_HUB_CACHE
echo "[$(date)] start install torch cpu"
$PIP install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu > /opt/AI-PM/install_embed.log 2>&1
echo "[$(date)] torch done, install FlagEmbedding"
$PIP install --no-cache-dir FlagEmbedding >> /opt/AI-PM/install_embed.log 2>&1
echo "[$(date)] FlagEmbedding done, verify import"
$VENV/bin/python -c "import torch, FlagEmbedding; print('OK torch', torch.__version__, 'FlagEmbedding ok')" >> /opt/AI-PM/install_embed.log 2>&1
echo "[$(date)] ALL DONE"
