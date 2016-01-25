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
import time

import pigpio
import umsgpack

# noinspection PyPackageRequirements
import zmq
# from pymata_aio.constants import Constants
# from pymata_aio.pymata3 import PyMata3

from xideco.data_files.port_map import port_map


# noinspection PyMethodMayBeStatic,PyUnresolvedReferences,PyUnresolvedReferences,PyUnresolvedReferences
class RaspberryPiBridge:
    """
    The Raspberry Bridge provides the protocol bridge between Xideco and a Raspberry Pi board using the
    pigpio library https://github.com/joan2937/pigpio

    """

    def __init__(self, pi, board_num):
        """
        :param pigpio: pigpio instance
        :param board_num: System Board Number (1-10)
        :return:
        """
        print('1-24-15  13:24')
        self.pi = pi

        # there are 3 types of raspberry pi boards dependent upon rev number:
        # http://elinux.org/RPi_HardwareHistory#Board_Revision_History

        # create a list of rev number to board type
        self.type_1_revs = [2, 3]
        self.type_2_revs = [4, 5, 6, 7, 8, 9, 13, 14, 15]
        # type_3 is >= 16 - this value will be used to compare against
        self.type_3_revs = 16

        # each board type supports a different set of GPIOs
        self.type_1_invalid_pins = [2, 3, 5, 6, 12, 13, 16, 19, 20, 26, 27, 28, 29, 30, 31]
        self.type_2_invalid_pins = [0, 1, 5, 6, 12, 13, 16, 19, 20, 21, 26]
        self.type_3_invalid_pins = [0, 1, 28, 29, 30, 31]

        # put them all in one list for simpler access
        self.unavailable_pins = [self.type_1_invalid_pins, self.type_2_invalid_pins,
                                 self.type_3_invalid_pins]

        # board type - 1, 2 or 3
        self.pi_board_type = None

        # a list of dictionary items, each entry is a single pin
        # dictionary entries are {mode, enabled}
        self.pins = []

        # set a list called pins to hold the pin modes
        for x in range(0, 32):
            mode = pi.get_mode(x)
            entry = {'mode': mode, 'enabled': False}
            self.pins.append(entry)

        # save user supplied board number
        self.board_num = board_num

        print("board num: " + board_num)

        # determine the hardware rev of the board
        hw_rev = self.pi.get_hardware_revision()
        print('HW REV: ' + str(hw_rev))

        # use that to set the board type
        if hw_rev >= self.type_3_revs:
            self.pi_board_type = 3
        elif hw_rev in self.type_1_revs:
            self.pi_board_type = 1
        elif hw_rev in self.type_2_revs:
            self.pi_board_type = 2
        else:
            print("Unknown Hardware Rev: " + hw_rev)
            sys.exit(0)

        print('Raspberry Pi Board Type Detected: ' + str(self.pi_board_type))

        pigpio_ver = self.pi.get_pigpio_version()
        print('PIGPIO REV: ' + str(pigpio_ver))

        # a list to hold prepared problem msgpack messages
        self.problem_list = []

        #     # for Snap - a dictionary of pins with their latest values
        #     self.digital_data = {}
        #     self.analog_data = {}
        #
        #
        #     # establish the zeriomq sub and pub sockets
        #
        self.context = zmq.Context()
        self.subscriber = self.context.socket(zmq.SUB)
        connect_string = "tcp://" + port_map.port_map['router_ip_address'] + ':' + port_map.port_map[
            'command_publisher_port']
        self.subscriber.connect(connect_string)

        # create the topic we wish to subscribe to
        env_string = "A" + self.board_num
        envelope = env_string.encode()
        self.subscriber.setsockopt(zmq.SUBSCRIBE, envelope)

        self.publisher = self.context.socket(zmq.PUB)
        connect_string = "tcp://" + port_map.port_map['router_ip_address'] + ':' + port_map.port_map[
            'reporter_publisher_port']

        self.publisher.connect(connect_string)

        # The Xideco protocol message received
        self.payload = None

        self.command_dict = {'digital_pin_mode': self.setup_digital_pin, 'digital_write': self.digital_write,
                             'analog_pin_mode': self.setup_analog_pin, 'analog_write': self.analog_write,
                             'set_servo_position': self.set_servo_position, 'play_tone': self.play_tone,
                             'tone_off': self.tone_off}

        self.last_problem = ''

    def setup_analog_pin(self):
        """
        This method validates and configures a pin for analog input
        :return: None
        """
        # clear out any residual problem strings
        #
        print('called setup_analog_pin')

    #
    #     self.report_problem(self.problem_list[0])
    #
    #     try:
    #         pin = int(self.payload['pin'])
    #     except ValueError:
    #         self.report_problem(self.problem_list[11])
    #         return
    #
    #     # validate that pin in the analog channel list
    #     # pin numbers start with 0
    #     if pin not in self.analog_channel:
    #         self.report_problem(self.problem_list[12])
    #         return
    #
    #     # Is the user enabling or disabling the pin? Get the 'raw' value and
    #     # translate it.
    #     enable = self.payload['enable']
    #
    #     if enable == 'Enable':
    #         self.board.set_pin_mode(pin, Constants.ANALOG, self.analog_input_callback)
    #     else:
    #         self.board.disable_analog_reporting(pin)
    #
    def setup_digital_pin(self):
        """
        This method processes the Scratch "Digital Pin" Block that establishes the mode for the pin
        :return: None
        """

        # clear out any residual problem strings
        # self.report_problem('1-0\n')
        self.last_problem = '1-0\n'

        pin = self.validate_pin()
        if pin == 99:
            self.last_problem = '1-1\n'
            return

        # Is the user enabling or disabling the pin? Get the 'raw' value and translate it.
        enable = self.payload['enable']

        # retrieve mode from command
        mode = self.payload['mode']
        #
        if enable == 'Enable':
            # validate the mode for this pin
            if mode == 'Input':
                self.pi.set_mode(pin, pigpio.INPUT)

                # update the pin table
                pin_entry = {'mode': pigpio.INPUT, 'enabled': True}
                self.pins[pin] = pin_entry
                self.pi.callback(pin, pigpio.EITHER_EDGE, self.cbf)
            elif mode == 'Output':
                self.pi.set_mode(pin, pigpio.OUTPUT)

                # update the pin table
                pin_entry = {'mode': pigpio.OUTPUT, 'enabled': True}
                self.pins[pin] = pin_entry

            elif mode == 'PWM':
                self.pi.set_mode(pin, pigpio.OUTPUT)

                # update the pin table
                pin_entry = {'mode': pigpio.OUTPUT, 'enabled': True}
                self.pins[pin] = pin_entry

            elif mode == 'Tone':
                self.pi.set_mode(pin, pigpio.OUTPUT)

                # update the pin table
                pin_entry = {'mode': pigpio.OUTPUT, 'enabled': True}
                self.pins[pin] = pin_entry

            elif mode == 'Servo':
                self.pi.set_mode(pin, pigpio.OUTPUT)

                # update the pin table
                pin_entry = {'mode': pigpio.OUTPUT, 'enabled': True}
                self.pins[pin] = pin_entry
                self.pi.set_mode(pin, pigpio.OUTPUT)

            elif mode == 'SONAR':
                self.pi.set_mode(pin, pigpio.INPUT)

                # update the pin table
                pin_entry = {'mode': pigpio.INPUT, 'enabled': True}
                self.pins[pin] = pin_entry
                self.pi.callback(pin, pigpio.EITHER_EDGE, self.cbf)
        # must be disable
        else:
            pin_entry = self.pins[pin]
            print(pin_entry)
            pin_entry['enabled'] = False
            pins[pin] = self.pin_entry
            print('b')

    #
    def analog_write(self):
        """
        Set a PWM configured pin to the requested value
        :return: None
        """
        print('analog_write')

        # clear out any residual problem strings
        self.last_problem = '4-0\n'

        pin = self.validate_pin()
        if pin == 99:
            self.last_problem = '4-1\n'
            return

        # get pin information
        pin_state = self.pins[pin]
        if pin_state['mode'] != pigpio.OUTPUT:
            self.last_problem = '4-2\n'
            return

        if not pin_state['enabled']:
            self.last_problem = '4-3\n'
            return

        value = int(self.payload['value'])
        #     self.board.digital_write(pin, value)
        self.pi.set_PWM_dutycycle(pin, value)

    def digital_write(self):
        """
        Set the state of a digital pin
        :return:
        """
        # clear out any residual problem strings
        self.last_problem = '3-0\n'

        pin = self.validate_pin()
        if pin == 99:
            self.last_problem = '3-1\n'
            return

        # get pin information
        pin_state = self.pins[pin]
        if pin_state['mode'] != pigpio.OUTPUT:
            self.last_problem = '3-2\n'
            return

        # if not pin_state['enabled']:
        #     self.last_problem = '3-3\n'
        #     return

        value = int(self.payload['value'])
        #     self.board.digital_write(pin, value)
        self.pi.write(pin, value)

    def play_tone(self):
        """
        This method will play a tone using the Arduino tone library. It requires FirmataPlus
        :return: None
        """
        # clear out any residual problem strings
        self.last_problem = '5-0\n'

        pin = self.validate_pin()
        if pin == 99:
            self.last_problem = '5-1\n'
            return

        # get pin information
        pin_state = self.pins[pin]
        if pin_state['mode'] != pigpio.OUTPUT:
            self.last_problem = '5-2\n'
            return
        frequency = int((1000 / int(self.payload['frequency'])) * 1000)
        duration = int(self.payload['duration'])

        tone = [pigpio.pulse(1 << pin, 0, frequency), pigpio.pulse(0, 1 << pin, frequency)]  # flash every 100 ms

        self.pi.wave_clear()

        self.pi.wave_add_generic(tone)  # 100 ms flashes
        tone_wave = self.pi.wave_create()  # create and save id
        self.pi.wave_send_repeat(tone_wave)

        if duration == 0:
            return

        sleep_time = duration * .001
        time.sleep(sleep_time)
        self.pi.wave_tx_stop()  # stop waveform

        self.pi.wave_clear()  # clear all waveforms

        print('play_tone')

    def tone_off(self):
        self.last_problem = '6-0\n'

        pin = self.validate_pin()
        if pin == 99:
            self.last_problem = '6-1\n'
            return

        self.pi.wave_tx_stop()  # stop waveform

        self.pi.wave_clear()  # clear all waveforms

    def set_servo_position(self):
        """
        Set a servo position
       :return:
        """
        print('set_servo')

        # time to allow servo to move
        delay = .6

        self.last_problem = '6-0\n'

        pin = self.validate_pin()
        if pin == 99:
            self.last_problem = '6-1\n'
            return

        # get pin information
        pin_state = self.pins[pin]
        if pin_state['mode'] != pigpio.OUTPUT:
            self.last_problem = '6-2\n'
            return

        position = int(self.payload['position'])


        # range of values for position is 500 to 2500
        # each degree is approximately equal to 11   (2000/180)
        # we add this to 500, the zerio degree position
        position = (position * 11) + 500

        self.pi.set_servo_pulsewidth(pin, position)  # 0 degree
        # print("Servo {} {} micro pulses".format(str(servos), 500))
        time.sleep(delay)
        self.pi.set_servo_pulsewidth(pin, 0)

    def run_raspberry_bridge(self):
        # self.pi.set_mode(11, pigpio.INPUT)
        # cb1 = self.pi.callback(11, pigpio.EITHER_EDGE, self.cbf)
        while True:
            if self.last_problem:
                self.report_problem()
            # noinspection PyBroadException
            try:
                z = self.subscriber.recv_multipart(zmq.NOBLOCK)
                self.payload = umsgpack.unpackb(z[1])
                print("[%s] %s" % (z[0], self.payload))

                command = self.payload['command']
                if command in self.command_dict:
                    self.command_dict[command]()
                else:
                    print("can't execute unknown command'")
                # time.sleep(.001)
            except KeyboardInterrupt:
                self.cleanup()
                sys.exit(0)
            except zmq.error.Again:
                time.sleep(.001)

    def report_problem(self):
        """
        Publish the supplied Xideco protocol message
        :return: None
        """
        # create a topic specific to the board number of this board
        envelope = ("B" + self.board_num).encode()

        msg = umsgpack.packb({u"command": "problem", u"board": 1, u"problem": self.last_problem})

        self.publisher.send_multipart([envelope, msg])
        self.last_problem = ''

    def cbf(self, gpio, level, tick):

        # if the pin has reports disabled, just ignore
        pin_state = self.pins[gpio]

        # if user changes modes suppress output from being sent upstream
        if pin_state['mode'] == pigpio.OUTPUT:
            return
        print(gpio, level, tick)
        digital_reply_msg = umsgpack.packb({u"command": "digital_read", u"pin": str(gpio), u"value": str(level)})

        envelope = ("B" + self.board_num).encode()
        self.publisher.send_multipart([envelope, digital_reply_msg])

    def cleanup(self):
        print('cleaning up')
        self.pi.stop()

    def validate_pin(self):
        """
        This method validates a pin number
        :return: Pin number if valid, 99 if invalid
        """
        # payload is established in run_raspberry_bridge
        try:
            pin = int(self.payload['pin'])
        except ValueError:
            # Pin Must Be Specified as an Integer 1-1
            return 99

        # check that pin does not exceed maximum BCM GPIO number
        if pin > 31:
            return 99

        # validate the gpio number for the board in use
        if pin in self.unavailable_pins[self.pi_board_type - 1]:
            return 99

        return pin


def raspberrypi_bridge():
    # noinspection PyShadowingNames

    parser = argparse.ArgumentParser()
    parser.add_argument("-b", dest="board_number", default="1", help="Board Number - 1 through 10")

    args = parser.parse_args()

    pi = pigpio.pi()

    board_num = args.board_number
    rpi_bridge = RaspberryPiBridge(pi, board_num)
    # while True:
    # rpi_bridge.run_raspberry_bridge()
    try:
        rpi_bridge.run_raspberry_bridge()
    except KeyboardInterrupt:
        print('done done')
        rpi_bridge.cleanup()
        pi.stop()
        sys.exit(0)

    # signal handler function called when Control-C occurs
    # noinspection PyShadowingNames,PyUnusedLocal,PyUnusedLocal
    def signal_handler(signal, frame):
        print("Control-C detected. See you soon.")
        sys.exit(0)

    # listen for SIGINT
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


if __name__ == "__main__":
    raspberrypi_bridge()
