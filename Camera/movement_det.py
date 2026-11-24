import secrets
import time
from signal import pause

import camera
from gpiozero import MotionSensor

pir = MotionSensor(25)
is_capturing = False


def movement_detected():
    global is_capturing

    if is_capturing:
        return

    is_capturing = True

    session_id = secrets.token_hex(16)

    for i in range(1, 6):
        current_filename = f"temp_{session_id}_{i}.jpg"
        camera.execute(session_id, current_filename)
        time.sleep(2)

    is_capturing = False


def no_movement():
    print("No movement...")


pir.when_activated = movement_detected
pir.when_deactivated = no_movement

print("Sensor is ready")
pause()
