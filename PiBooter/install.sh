#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_TEMPLATE="$SCRIPT_DIR/boot/pibooter.service"
SERVICE_TARGET="/etc/systemd/system/pibooter.service"
CONFIG_PATH="$SCRIPT_DIR/config/settings.json"
TMP_SERVICE="$(mktemp)"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required." >&2
  exit 1
fi

mkdir -p "$SCRIPT_DIR/runtime"
python3 "$SCRIPT_DIR/run_pibooter.py" --config "$CONFIG_PATH" --write-default-config >/dev/null

sed "s|__PIBOOTER_DIR__|$SCRIPT_DIR|g" "$SERVICE_TEMPLATE" > "$TMP_SERVICE"
sudo cp "$TMP_SERVICE" "$SERVICE_TARGET"
rm -f "$TMP_SERVICE"

sudo systemctl daemon-reload
sudo systemctl enable pibooter.service >/dev/null
sudo systemctl restart pibooter.service

if command -v nmcli >/dev/null 2>&1; then
  echo "nmcli detected."
else
  echo "WARNING: nmcli / NetworkManager was not found. PiBooter's web page will start, but Wi-Fi onboarding will not work until NetworkManager is installed and enabled." >&2
fi

HOTSPOT_PASSWORD="$(python3 - "$CONFIG_PATH" <<'PY'
import json
import sys
from pathlib import Path
path = Path(sys.argv[1])
config = json.loads(path.read_text(encoding='utf-8'))
print(config.get('network', {}).get('hotspot_password', 'pibooter1234'))
PY
)"

STARTUP_WAIT="$(python3 - "$CONFIG_PATH" <<'PY'
import json
import sys
from pathlib import Path
path = Path(sys.argv[1])
config = json.loads(path.read_text(encoding='utf-8'))
print(config.get('server', {}).get('startup_wait_s', 5))
PY
)"

echo
echo "PiBooter installed."
echo "Service: pibooter.service"
echo "Project dir: $SCRIPT_DIR"
echo "Config: $CONFIG_PATH"
echo
echo "Default hotspot password: $HOTSPOT_PASSWORD"
echo "Startup wait window: ${STARTUP_WAIT}s"
echo
echo "Check service status with: sudo systemctl status pibooter.service"
