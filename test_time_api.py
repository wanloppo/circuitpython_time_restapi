# OLED Pinout : GP6 - SDA, GP7 - SCL
# Installing CircuitPython - https://learn.adafruit.com/getting-started-with-raspberry-pi-pico-circuitpython/circuitpython
import time
import busio
from adafruit_espatcontrol import adafruit_espatcontrol
import board
import time_api as t
import rtc

sleep_duration = 5

try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise
# Initialize UART connection to the ESP8266 WiFi Module.
RX = board.GP17
TX = board.GP16
uart = busio.UART(
    TX, RX, receiver_buffer_size=2048
)  # Use large buffer as we're not using hardware flow control.

esp = adafruit_espatcontrol.ESP_ATcontrol(uart, 115200, debug=False)

the_rtc = rtc.RTC()
time_api = t.Time_Api(esp,secrets)
time_api.connect()
the_rtc = time_api.get_time()

print(the_rtc.datetime)
while True:
    str_date = str(the_rtc.datetime.tm_year) + '-' + str(the_rtc.datetime.tm_mon) + '-' +  str(the_rtc.datetime.tm_mday)
    str_time = str(the_rtc.datetime.tm_hour) + ':' + str(the_rtc.datetime.tm_min) + ':' +  str(the_rtc.datetime.tm_sec)
    print(str_date + ' ' + str_time)
    time.sleep(sleep_duration)


