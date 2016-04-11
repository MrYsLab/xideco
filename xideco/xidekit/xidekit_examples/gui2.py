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
import time
from tkinter import *
from tkinter import ttk

import umsgpack
import zmq

from xideco.xidekit.xidekit import XideKit


# noinspection PyMethodMayBeStatic,PyUnresolvedReferences
class Gui(XideKit):
    def __init__(self, router_ip_address=None, subscriber_port='43125', publisher_port='43124'):
        """

        :param router_ip_address: ip address of router
        :param subscriber_port: router subscriber port
        :param publisher_port: router publisher port
        :return:
        """
        super().__init__(router_ip_address, subscriber_port, publisher_port)

        # get instance of Tk and set as root
        self.root = Tk()

        # set the window title
        self.root.title('Xideco Arduino/Gui Demo')

        # create the main frame, add a grid and configure the frame
        self.mainframe = ttk.Frame(self.root, padding="2 2 12 12")
        self.mainframe.grid(column=0, row=0, sticky=(N, W, E, S))
        self.mainframe.columnconfigure(0, weight=1)
        self.mainframe.rowconfigure(0, weight=1)

        # add a button that will ultimately turn an LED on and OFF the remote Arduino
        self.led = Button(self.mainframe, text="Blue LED On", command=self.on, background='red', width="30")
        self.led.grid(column=2, row=1, sticky=W)

        # add a label that will ultimately display the current value of a potentiometer connected to the remote
        # arduino.
        self.pot = Label(self.mainframe, text="No Data Received Yet", width="30")
        self.pot.grid(column=2, row=2, sticky=W)

        # adjust the layout with some padding
        for child in self.mainframe.winfo_children():
            child.grid_configure(padx=5, pady=5)
        self.mainframe.focus()

        # set up pin modes on arduino
        # digital output for pin 9
        cmd = {u"command": "digital_pin_mode", u"enable": "Enable", u"pin": "9", u"mode": "Output"}
        self.publish_payload(cmd, "A1")

        # analog input for pin A2
        cmd = {u"command": "analog_pin_mode", u"enable": "Enable", u"pin": "2"}
        self.publish_payload(cmd, "A1")

    def on(self):
        """
        When the button is pressed and going to an ON state, this method is called
        :return:
        """
        command = "digital_write"
        pin = 9
        value = 1

        cmd = {u"command": command, u"pin": pin, u"value": value}
        self.led.configure(bg='#00CC00', text="LED Off", command=self.off)
        # print('LED On')
        self.publish_payload(cmd, "A1")

    def off(self):
        """
        When the button is pressed and going to an OFF state, this method is called
        :return:
        """
        command = "digital_write"
        pin = 9
        value = 0
        self.led.configure(bg='#FF0101', text="LED On", command=self.on)
        # print('LED Off')
        cmd = {u"command": command, u"pin": pin, u"value": value}

        self.publish_payload(cmd, "A1")

    def receive_loop(self):
        """
        This is the receive loop for zmq messages
        It is assumed that this method may be overwritten to meet the needs of the application
        It returns payload via user provided callback method
        :return:
        """
        while True:
            try:
                data = self.subscriber.recv_multipart(zmq.NOBLOCK)
                self.incoming_message_processing(data[0].decode(), umsgpack.unpackb(data[1]))
                time.sleep(.001)
            except zmq.error.Again:
                try:
                    time.sleep(.001)
                    self.root.update()
                except KeyboardInterrupt:
                    self.root.destroy()
                    self.publisher.close()
                    self.subscriber.close()
                    self.context.term()
                    sys.exit(0)
            except KeyboardInterrupt:
                self.root.destroy()
                self.publisher.close()
                self.subscriber.close()
                self.context.term()
                sys.exit(0)

    def incoming_message_processing(self, topic, payload):
        """
        This is the message processor
        :param topic: topic string
        :param payload: message data
        :return:
        """
        # extract the command from the message dictionary
        if payload['command'] == 'analog_read':
            data = str(payload['value'])

            # this should be an updated potentiometer value, so update the gui with the new value
            self.pot.configure(text=data)


if __name__ == '__main__':
    gui = Gui()
    gui.set_subscriber_topic('B1')
    # noinspection PyBroadException
    try:
        gui.receive_loop()
    except Exception:
        sys.exit(0)
