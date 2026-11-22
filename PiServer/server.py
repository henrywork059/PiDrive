import os

from piserver import create_app
from piserver.core.access_control import select_bind_host

BIND_HOST = select_bind_host()  # Reject unsafe remote binding before hardware services start.
app = create_app()

if __name__ == "__main__":
    app.run(host=BIND_HOST, port=int(os.environ.get("PISERVER_PORT", "5000")), threaded=True)
