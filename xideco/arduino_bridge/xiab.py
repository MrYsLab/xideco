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

import argparse
import signal
import sys

import umsgpack
# noinspection PyPackageRequirements
import zmq
from pymata_aio.constants import Constants
from pymata_aio.pymata3 import PyMata3

from xideco.data_files.port_map import port_map


# noinspection PyMethodMayBeStatic,PyUnresolvedReferences,PyUnresolvedReferences,PyUnresolvedReferences
class ArduinoBridge:
    """
    The Arduino Bridge provides the protocol bridge between Xideco and Firmata
    """

    def __init__(self, pymata_board, board_num, router_ip_address):
        """
        :param pymata_board: Pymata-aio instance
        :param board_num: Arduino Board Number (1-10)
        :return:
        """

        self.board_num = board_num
        self.board = pymata_board
        self.router_ip_address = router_ip_address


        # lists of digital pin capabilities
        # These lists contain the pins numbers that support the capability
        self.input_capable = []
        self.output_capable = []
        self.analog_capable = []
        self.pwm_capable = []
        self.servo_capable = []
        self.i2c_capable = []

        # this contains the numeric "A" (A0, A1..) channel values supported by the board
        self.analog_channel = []

        # this is the total number of pins supported by the connected arduino
        self.num_digital_pins = 0

        # for Snap - a dictionary of pins with their latest values
        self.digital_data = {}
        self.analog_data = {}

        # go discover the type of Arduino that we are connected to
        self.get_pin_capabilities()

        # establish the zeriomq sub and pub sockets
        if self.router_ip_address == 'None':
            self.router_ip_address = port_map.port_map['router_ip_address']
        else:
            self.router_ip_address = router_ip_address

        print('\n**************************************')
        print('Arduino Bridge - xiab')
        print('Using router IP address: ' + self.router_ip_address)
        print('**************************************')

        print('\nTo specify some other address for the router, use the -r command line option')

        # establish the zeriomq sub and pub sockets
        self.context = zmq.Context()
        self.subscriber = self.context.socket(zmq.SUB)
        connect_string = "tcp://" + self.router_ip_address + ':' + port_map.port_map['subscribe_to_router_port']
        self.subscriber.connect(connect_string)

        # create the topic we wish to subscribe to
        env_string = "A" + self.board_num
        envelope = env_string.encode()
        self.subscriber.setsockopt(zmq.SUBSCRIBE, envelope)
        # subscribe to broadcast i2c message - i2c messages can also be board specific with A + board number
        self.subscriber.setsockopt(zmq.SUBSCRIBE, 'Q'.encode())

        self.publisher = self.context.socket(zmq.PUB)
        connect_string = "tcp://" + self.router_ip_address + ':' + port_map.port_map['publish_to_router_port']

        self.publisher.connect(connect_string)

        # The Xideco protocol message received
        self.payload = None

        # "pointers" to the methods to process commands from the user
        self.command_dict = {'digital_pin_mode': self.setup_digital_pin, 'digital_write': self.digital_write,
                             'analog_pin_mode': self.setup_analog_pin, 'analog_write': self.analog_write,
                             'set_servo_position': self.set_servo_position, 'play_tone': self.play_tone,
                             'tone_off': self.tone_off, 'i2c_request': self.i2c_request}

        self.last_problem = ''

        self.i2c_report_pending = False

    def setup_analog_pin(self):
        """
        This method validates and configures a pin for analog input
        :return: None
        """
        # clear out any residual problem strings
        self.last_problem = '2-0\n'
        self.report_problem()

        try:
            pin = int(self.payload['pin'])
        except ValueError:
            self.last_problem = '2-1\n'
            return

        # validate that pin in the analog channel list
        # pin numbers start with 0
        if pin not in self.analog_channel:
            self.last_problem = '2-2\n'
            return

        # Is the user enabling or disabling the pin? Get the 'raw' value and
        # translate it.
        enable = self.payload['enable']

        if enable == 'Enable':
            self.board.set_pin_mode(pin, Constants.ANALOG, self.analog_input_callback)
        else:
            self.board.disable_analog_reporting(pin)

    def setup_digital_pin(self):
        """
        This method processes the Scratch "Digital Pin" Block that establishes the mode for the pin
        :return: None
        """

        # clear out any residual problem strings
        self.last_problem = '1-0\n'

        # convert pin string to integer.
        try:
            pin = int(self.payload['pin'])
        except ValueError:
            # Pin Must Be Specified as an Integer 1-1
            self.last_problem = '1-1\n'
            return

        # validate that the pin is within the pin count range
        # pin numbers start with 0 1-2
        if pin >= self.num_digital_pins:
            self.last_problem = '1-2\n'
            return

        # Is the user enabling or disabling the pin? Get the 'raw' value and translate it.
        enable = self.payload['enable']

        # retrieve mode from command
        mode = self.payload['mode']

        if enable == 'Enable':
            # validate the mode for this pin
            if mode == 'Input':
                if pin in self.input_capable:
                    # send the pin mode to the arduino
                    self.board.set_pin_mode(pin, Constants.INPUT, self.digital_input_callback)
                else:
                    # this pin does not support input mode
                    self.last_problem = '1-3\n'
            # elif mode == 'Output':
            elif mode == 'Output':
                if pin in self.output_capable:
                    # send the pin mode to the arduino
                    self.board.set_pin_mode(int(pin), Constants.OUTPUT)
                else:
                    # this pin does not support output mode
                    self.last_problem = '1-4\n'

            elif mode == 'PWM':
                if pin in self.pwm_capable:
                    # send the pin mode to the arduino
                    self.board.set_pin_mode(pin, Constants.PWM)
                else:
                    # this pin does not support output mode
                    self.last_problem = '1-5\n'
            elif mode == 'Servo':
                if pin in self.servo_capable:
                    # send the pin mode to the arduino
                    self.board.set_pin_mode(pin, Constants.SERVO)
                else:
                    # this pin does not support output mode
                    self.last_problem = '1-6\n'
            elif mode == 'Tone':
                if pin in self.servo_capable:
                    # send the pin mode to the arduino
                    self.board.set_pin_mode(pin, Constants.OUTPUT)
                else:
                    # this pin does not support output mode
                    self.last_problem = '1-7\n'
            elif mode == 'SONAR':
                if pin in self.input_capable:
                    # send the pin mode to the arduino
                    self.board.sonar_config(pin, pin, self.digital_input_callback, Constants.CB_TYPE_ASYNCIO)
                else:
                    # this pin does not support output mode
                    self.last_problem = '1-8\n'
            else:
                self.last_problem = '1-9\n'
        # must be disable
        else:
            pin_state = self.board.get_pin_state(pin)
            if pin_state[1] != Constants.INPUT:
                self.last_problem = '1-10\n'
            else:
                # disable the pin
                self.board.disable_digital_reporting(pin)

    def analog_write(self):
        """
        Set a PWM configured pin to the requested value
        :return: None
        """

        self.last_problem = '4-0\n'
        # clear out any residual problem strings

        try:
            pin = int(self.payload['pin'])
        except ValueError:
            # Pin Must Be Specified as an Integer
            self.last_problem = '4-1\n'
            return

        pin_state = self.board.get_pin_state(pin)
        if len(pin_state) == 1:
            self.last_problem = '4-2\n'
            return

        if pin_state[1] != Constants.PWM:
            self.last_problem = '4-3\n'
            return

        try:
            value = int(self.payload['value'])
        except ValueError:
            # Pin Must Be Specified as an Integer
            self.last_problem = '4-4\n'
            return

        # validate range of value
        if 0 <= value <= 255:
            self.board.analog_write(pin, value)
        else:
            self.last_problem = '4-5\n'

    def digital_write(self):
        """
        Set the state of a digital pin
        :return:
        """

        # clear out any residual problem strings
        self.last_problem = '3-0\n'

        try:
            pin = int(self.payload['pin'])
        except ValueError:
            self.last_problem = '3-1\n'
            return

        pin_state = self.board.get_pin_state(pin)
        if len(pin_state) == 1:
            self.last_problem = '3-2\n'
            return

        if pin_state[1] != Constants.OUTPUT:
            self.last_problem = '3-3\n'
            return

        value = int(self.payload['value'])
        self.board.digital_write(pin, value)

    def play_tone(self):
        """
        This method will play a tone using the Arduino tone library. It requires FirmataPlus
        :return: None
        """
        # clear out any residual problem strings
        self.last_problem = '5-0\n'
        # get the pin string from the block
        try:
            pin = int(self.payload['pin'])
        except ValueError:
            # Pin Must Be Specified as an Integer
            self.last_problem = '5-1\n'
            return

        pin_state = self.board.get_pin_state(pin)
        if len(pin_state) == 1:
            self.last_problem = '5-2\n'
            return

        if pin_state[1] != Constants.OUTPUT:
            self.last_problem = '5-3\n'
            return

        frequency = self.payload['frequency']

        try:
            frequency = int(frequency)
        except ValueError:
            # frequency Must Be Specified as an Integer
            self.last_problem = '5-4\n'
            return

        try:
            duration = int(self.payload['duration'])
        except ValueError:
            # frequency Must Be Specified as an Integer
            self.last_problem = '5-5\n'
            return

        self.board.play_tone(pin, Constants.TONE_TONE, frequency, duration)

    def tone_off(self):
        """
        Turn tone off
        :return:
        """
        # clear out any residual problem strings
        self.last_problem = '6-0\n'
        # get the pin string from the block
        try:
            pin = int(self.payload['pin'])
        except ValueError:
            # Pin Must Be Specified as an Integer
            self.last_problem = '6-1\n'
            return

        pin_state = self.board.get_pin_state(pin)
        if len(pin_state) == 1:
            self.last_problem = '6-2\n'
            return

        if pin_state[1] != Constants.OUTPUT:
            self.last_problem = '6-3\n'
            return

        self.board.play_tone(pin, Constants.TONE_NO_TONE, None, None)
        return

    def set_servo_position(self):
        """
        Set a servo position
        :return:
        """
        # clear out any residual problem strings
        self.last_problem = '7-0\n'

        try:
            pin = int(self.payload['pin'])
        except ValueError:
            self.last_problem = '7-1\n'
            return

        pin_state = self.board.get_pin_state(pin)
        if len(pin_state) == 1:
            self.last_problem = '7-2\n'
            return

        if pin_state[1] != Constants.SERVO:
            self.last_problem = '7-3\n'
            return

        position = self.payload['position']

        try:
            position = int(position)
        except ValueError:
            # frequency Must Be Specified as an Integer
            self.last_problem = '7-4\n'
            return

        if 0 <= position <= 180:
            self.board.analog_write(pin, position)
        else:
            self.last_problem = '7-5\n'
        return

    def digital_input_callback(self, data):
        """
        This method receives digital data inputs, creates a Xideco protocol publishing message and publishes the message
        :param data: data[0] = pin, data[1] = value
        :return: None
        """
        pin = str(data[0])
        value = str(data[1])

        digital_reply_msg = umsgpack.packb({u"command": "digital_read", u"pin": pin, u"value": value})

        envelope = ("B" + self.board_num).encode()
        self.publisher.send_multipart([envelope, digital_reply_msg])
        # print(digital_reply_msg)
        # print(envelope)

    def analog_input_callback(self, data):
        """
        This method receives Analog data inputs, creates a Xideco protocol publishing message and publishes the message
        :param data: data[0] = pin, data[1] = value
        :return: None
        """
        pin = str(data[0])
        value = str(data[1])

        analog_reply_msg = umsgpack.packb({u"command": "analog_read", u"pin": pin, u"value": value})

        envelope = ("B" + self.board_num).encode()
        self.publisher.send_multipart([envelope, analog_reply_msg])

    def i2c_request(self):
        """
        This method parses the i2c request and translates it to a native request
        :return:
        """
        while self.i2c_report_pending:
            self.board.sleep(.001)
        cmd = self.payload['cmd']
        addr = self.payload['device_address']

        if cmd == 'init':
            self.board.i2c_config()
        elif cmd == 'write_byte':
            # get handle
            value = self.payload['value']
            register = self.payload['register']
            self.board.i2c_write_request(addr, [register, value])
        elif cmd == 'read_block':
            num_bytes = self.payload['num_bytes']
            register = self.payload['register']
            self.i2c_report_pending = True

            self.board.i2c_read_request(addr, register, num_bytes, Constants.I2C_READ, self.report_i2c_data)
            self.board.sleep(.001)
        else:
            print('unknown cmd')

    def report_i2c_data(self, data):
        # create a topic specific to the board number of this board
        envelope = ("B" + self.board_num).encode()

        msg = umsgpack.packb({u"command": "i2c_reply", u"board": self.board_num, u"data": data[2:]})

        self.publisher.send_multipart([envelope, msg])
        self.i2c_report_pending = False


    def run_arduino_bridge(self):
        """
        start the bridge
        :return:
        """

        while True:
            if self.last_problem:
                self.report_problem()
            # noinspection PyBroadException
            try:
                z = self.subscriber.recv_multipart(zmq.NOBLOCK)

                self.payload = umsgpack.unpackb(z[1])
                # print("[%s] %s" % (z[0], self.payload))
                command = self.payload['command']
                if command in self.command_dict:
                    self.command_dict[command]()
                else:
                    print("can't execute unknown command'")
                self.board.sleep(.001)
            except zmq.error.Again:
                self.board.sleep(.001)
            # return

    def get_pin_capabilities(self):
        """
        This method retrieves the Arduino pin capability and analog map reports.
        For each digital pin mode, a list of valid pins is constructed,
        A total pin count is calculated and in addition,
        a list of valid analog input channels is constructed.
        :return: None
        """
        # get the capability report
        pin_capabilities = self.board.get_capability_report()

        # initialize the total pin count to o
        pin_count = 0

        pin_data = []

        # Each set of digital pin capabilities is delimited by the value of 127
        # Accumulate all of the capabilities into a list for the current pin
        for x in pin_capabilities:
            if x != 127:
                pin_data.append(x)
                continue
            # Found a delimiter, populate the specific capability lists with this pin.
            # Each capability contains 2 bytes. The first is the capability and the second is the
            # number of bits of data resolution for the pin. The resolution is ignored
            else:
                pin__x_capabilities = pin_data[::2]
                for y in pin__x_capabilities:
                    if y == 0:
                        self.input_capable.append(pin_count)
                    elif y == 1:
                        self.output_capable.append(pin_count)
                    elif y == 2:
                        self.analog_capable.append(pin_count)
                    elif y == 3:
                        self.pwm_capable.append(pin_count)
                    elif y == 4:
                        self.servo_capable.append(pin_count)
                    elif y == 6:
                        self.i2c_capable.append(pin_count)
                    elif 7 < y < 14:
                        pass
                    else:
                        print('Unknown Pin Type ' + str(y))
                # clear the pin_data list for the next pin and bump up the pin count
                pin_data = []
                # add an entry into the digital data dictionary
                self.digital_data[pin_count] = 0

                pin_count += 1
        # Done with digital pin discovery, save the pin count
        self.num_digital_pins = pin_count

        # Get analog channel data and create the analog_channel list
        analog_pins = self.board.get_analog_map()
        for x in analog_pins:
            if x != 127:
                self.analog_channel.append(x)
                self.analog_data[x] = 0

    # def report_problem(self, problem):
    def report_problem(self):

        """
        Publish the supplied Xideco protocol message
        :return:
        """
        # create a topic specific to the board number of this board
        # envelope = ("B" + self.board_num).encode()
        # self.publisher.send_multipart([envelope, problem])

        envelope = ("B" + self.board_num).encode()

        msg = umsgpack.packb({u"command": "problem", u"board": 1, u"problem": self.last_problem})

        self.publisher.send_multipart([envelope, msg])
        self.last_problem = ''

    def clean_up(self):
        """
        Clean things up on exit
        :return:
        """
        self.subscriber.close()
        self.publisher.close()
        self.context.term()


def arduino_bridge():
    """
    Main function for arduino bridge
    :return:
    """
    # noinspection PyShadowingNames

    parser = argparse.ArgumentParser()
    parser.add_argument("-b", dest="board_number", default="1", help="Board Number - 1 through 10")
    parser.add_argument("-p", dest="comport", default="None", help="Arduino COM port - e.g. /dev/ttyACMO or COM3")
    parser.add_argument('-r', dest='router_ip_address', default='None', help='Router IP Address')


    args = parser.parse_args()
    if args.comport == "None":
        pymata_board = PyMata3()
    else:
        pymata_board = PyMata3(com_port=args.comport)

    board_num = args.board_number

    router_ip_address = args.router_ip_address

    abridge = ArduinoBridge(pymata_board, board_num, router_ip_address)
    # while True:
    abridge.run_arduino_bridge()

    # signal handler function called when Control-C occurs
    # noinspection PyShadowingNames,PyUnusedLocal,PyUnusedLocal
    def signal_handler(signal, frame):
        print("Control-C detected. See you soon.")

        abridge.clean_up()

        sys.exit(0)

    # listen for SIGINT
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


if __name__ == "__main__":

    try:
        arduino_bridge()
    except KeyboardInterrupt:
        sys.exit(0)
