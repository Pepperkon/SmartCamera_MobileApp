from gpiozero import MotionSensor
from signal import pause
import camera

pir = MotionSensor(25)

def movement_detected():
    camera.execute()

def no_movement():
    print('No movement...')

pir.when_activated = movement_detected
pir.when_deactivated = no_movement

print('Sensor is ready')
pause()
