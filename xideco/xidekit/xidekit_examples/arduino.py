#!/usr/bin/env python3

"""
Created on January 9 11:39:15 2016

@author: Alan Yorinks
Copyright (c) 2016 Alan Yorinks All right reserved.

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public
License as published by the Free Software Foundation; either
version 3 of the License, or (at your option) any later version.

This library is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
General Public License for more details.

You should have received a copy of the GNU Lesser General Public
License along with this library; if not, write to the Free Software
Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
"""
import asyncio

import umsgpack
import zmq
from pymata_aio.constants import Constants
from pymata_aio.pymata3 import PyMata3

from xideco.xidekit.xidekit import XideKit


class Arduino(XideKit):
    """
    The Arduino class encapsulates a PyMata3 instance to control a digital output pin
    and to receive data updates from an analog input pin.
    """
    # Constants
    BLUE_LED = 9  # digital pin number of blue LED
    POTENTIOMETER = 2  # analog pin number for the potentiometer
    DATA = 1  # position in callback data for current data value

    def __init__(self, router_ip_address=None, subscriber_port='43125', publisher_port='43124'):
        """
        This method instantiates a PyMata3 instance. It sets pin 9 as a digital output and analog pin 2 as sn input.
        A callback method is associated with the analog input pin to report the current value.

        :return:
        """
        super().__init__(router_ip_address, subscriber_port, publisher_port)

        self.board = PyMata3()
        self.board.set_pin_mode(self.BLUE_LED, Constants.OUTPUT)
        self.board.set_pin_mode(self.POTENTIOMETER, Constants.ANALOG, self.analog_callback)

    def analog_callback(self, data):
        """
        The method that PyMata3 calls when an analog value is being reported
        :param data: A list with the 2nd element containing the current value of the potentiometer
        :return:
        """
        value = str(data[self.DATA])
        self.publish_payload({'command': value}, "A")
        self.board.sleep(.001)

    def receive_loop(self):
        """
        This is the receive loop for zmq messages
        It is assumed that this method will be overwritten to meet the needs of the application and to handle
        received messages.
        :return:
        """
        while True:
            try:
                data = self.subscriber.recv_multipart(zmq.NOBLOCK)
                self.incoming_message_processing(data[0].decode(), umsgpack.unpackb(data[1]))
                self.board.sleep(.001)
            except zmq.error.Again:
                try:
                    self.board.sleep(.001)
                except:
                    self.clean_up()
            except KeyboardInterrupt:
                self.clean_up()

    # noinspection PyMethodMayBeStatic
    def incoming_message_processing(self, topic, payload):
        """
        This method is overwritten in the inherited class to process the data
        :param topic: topic string
        :param payload: message data
        :return:
        """
        command = payload['command']
        if command == 'On':
            asyncio.ensure_future(self.board.core.digital_write(self.BLUE_LED, 1))
        elif command == 'Off':
            asyncio.ensure_future(self.board.core.digital_write(self.BLUE_LED, 0))
        self.board.sleep(.1)


if __name__ == "__main__":
    arduino = Arduino()
    arduino.set_subscriber_topic('B')
    arduino.receive_loop()
