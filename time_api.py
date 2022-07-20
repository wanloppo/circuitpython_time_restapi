# SPDX-FileCopyrightText: 2019 Melissa LeBlanc-Williams for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import errno
import struct
from random import randint
from micropython import const
from .matcher import MQTTMatcher

import time
import board
import busio
from digitalio import DigitalInOut
from digitalio import Direction
import rtc
import adafruit_requests as requests
import adafruit_espatcontrol.adafruit_espatcontrol_socket as socket
import adafruit_espatcontrol
try:
    from typing import Dict, Any, Optional, Union, Tuple
    from circuitpython_typing.led import FillBasedLED
    from adafruit_espatcontrol.adafruit_espatcontrol import ESP_ATcontrol
except ImportError:
    pass

CONNACK_ERRORS = {
    const(0x01): "Connection Refused - Incorrect Protocol Version",
    const(0x02): "Connection Refused - ID Rejected",
    const(0x03): "Connection Refused - Server unavailable",
    const(0x04): "Connection Refused - Incorrect username/password",
    const(0x05): "Connection Refused - Unauthorized",
}

_default_sock = None  # pylint: disable=invalid-name
_fake_context = None  # pylint: disable=invalid-name

def set_socket(sock, iface=None):
    """Legacy API for setting the socket and network interface.

    :param sock: socket object.
    :param iface: internet interface object

    """
    global _default_sock  # pylint: disable=invalid-name, global-statement
    global _fake_context  # pylint: disable=invalid-name, global-statement
    _default_sock = sock


class Time_Api:
    """
    A class to help manage the Wifi connection
    """

    def __init__(
        self,
        esp: ESP_ATcontrol,
        secrets: Dict[str, Union[str, int]],
        status_pixel: Optional[FillBasedLED] = None,
        attempts: int = 2,
    ):
        """
        :param ESP_SPIcontrol esp: The ESP object we are using
        :param dict secrets: The WiFi and Adafruit IO secrets dict (See examples)
        :param status_pixel: (Optional) The pixel device - A NeoPixel or DotStar (default=None)
        :type status_pixel: NeoPixel or DotStar
        :param int attempts: (Optional) Failed attempts before resetting the ESP32 (default=2)
        """
        # Read the settings
        self._esp = esp
        self.debug = False
        self.secrets = secrets
        self.attempts = attempts
        requests.set_socket(socket, esp)
        self.statuspix = status_pixel
        self.pixel_status(0)

    def reset(self) -> None:
        """
        Perform a hard reset on the ESP
        """
        if self.debug:
            print("Resetting ESP")
        self._esp.hard_reset()

    def connect(self) -> None:
        """
        Attempt to connect to WiFi using the current settings
        """
        failure_count = 0
        while not self._esp.is_connected:
            try:
                if self.debug:
                    print("Connecting to AP...")
                self.pixel_status((100, 0, 0))
                self._esp.connect(self.secrets)
                failure_count = 0
                self.pixel_status((0, 100, 0))
            except (ValueError, RuntimeError) as error:
                print("Failed to connect, retrying\n", error)
                failure_count += 1
                if failure_count >= self.attempts:
                    failure_count = 0
                    self.reset()
                continue

    def get(self, url: str, **kw: Any) -> requests.Response:
        """
        Pass the Get request to requests and update Status NeoPixel

        :param str url: The URL to retrieve data from
        :param dict data: (Optional) Form data to submit
        :param dict json: (Optional) JSON data to submit. (Data must be None)
        :param dict header: (Optional) Header data to include
        :param bool stream: (Optional) Whether to stream the Response
        :return: The response from the request
        :rtype: Response
        """
        if not self._esp.is_connected:
            self.connect()
        self.pixel_status((0, 0, 100))
        return_val = requests.get(url, **kw)
        self.pixel_status(0)
        return return_val
        
    def get_time(self, **kw: Any) -> requests.Response:
        TIME_API = "http://worldtimeapi.org/api/ip"
        response = None 
        while True:
            try:
                print("Fetching json from", TIME_API)
                response = self.get(TIME_API)
                break
            except (ValueError, RuntimeError, adafruit_espatcontrol.OKError) as e:
                print("Failed to get data, retrying\n", e)
                continue        
        the_rtc = rtc.RTC()
        json = response.json()
        current_time = json["datetime"]
        the_date, the_time = current_time.split("T")
        year, month, mday = [int(x) for x in the_date.split("-")]
        the_time = the_time.split(".")[0]
        hours, minutes, seconds = [int(x) for x in the_time.split(":")]

        # We can also fill in these extra nice things
        year_day = json["day_of_year"]
        week_day = json["day_of_week"]
        is_dst = json["dst"]

        now = time.struct_time(
            (year, month, mday, hours, minutes, seconds, week_day, year_day, is_dst)
        )
        the_rtc.datetime = now

        return_val = the_rtc
        return return_val

    def pixel_status(self, value: Union[int, Tuple[int, int, int]]) -> None:
        """
        Change Status NeoPixel if it was defined

        :param value: The value to set the Board's Status NeoPixel to
        :type value: int or 3-value tuple
        """
        if self.statuspix:
            self.statuspix.fill(value)

