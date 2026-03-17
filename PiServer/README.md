# PiServer

PiServer is the modular PiCar web-control backend.

Compared with the legacy `piCar_0_3_2` runtime, this project separates concerns into app/core/services/algorithms/web modules and keeps a persistent service-oriented architecture.

## Layout

```text
PiServer/
├── server.py
├── requirements.txt
├── config/runtime.json
├── boot/pi_server.service
├── piserver/
│   ├── app.py
│   ├── core/
│   ├── services/
│   ├── algorithms/
│   └── web/
└── PATCH_NOTES/
```

## Install and run

```bash
cd PiServer
python3 -m pip install -r requirements.txt
python3 server.py
```

Open in browser:

```text
http://<pi-ip>:5000
```

## Runtime modules

- `services/camera_service.py`: camera backend and frame access.
- `services/motor_service.py`: motor output abstraction/safety limits.
- `services/control_service.py`: control loop and algorithm dispatch.
- `services/recorder_service.py`: session recording/output format.
- `services/model_service.py`: model upload/list/load integration.
- `algorithms/`: `manual`, `stop`, `auto_steer`, `autopilot` implementations.

## Optional Raspberry Pi dependencies

PiServer can run with reduced capability if Pi-specific libs are unavailable.

Optional packages:

- `picamera2`
- `tflite-runtime`
- `RPi.GPIO`

## systemd auto-start (optional)

```bash
sudo cp boot/pi_server.service /etc/systemd/system/pi_server.service
sudo systemctl daemon-reload
sudo systemctl enable pi_server.service
sudo systemctl start pi_server.service
```

Update `WorkingDirectory`/`ExecStart` in the service file if your install path differs.
