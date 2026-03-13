from __future__ import annotations

from pathlib import Path
import importlib.util

APP_PATH = Path(__file__).resolve().parent / "piserver" / "app.py"
spec = importlib.util.spec_from_file_location("piserver_app_runtime", APP_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Cannot load app module from {APP_PATH}")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

if not hasattr(module, "create_app"):
    raise RuntimeError("piserver/app.py does not define create_app()")

app = module.create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
