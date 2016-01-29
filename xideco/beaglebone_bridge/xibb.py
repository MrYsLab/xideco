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
import time

import umsgpack
# noinspection PyPackageRequirements
import zmq
from xideco.data_files.port_map import port_map

import signal
import sys

import Adafruit_BBIO.GPIO as GPIO
import Adafruit_BBIO.PWM as PWM


# noinspection PyMethodMayBeStatic,PyUnresolvedReferences,PyUnresolvedReferences,PyUnresolvedReferences
class BeagleBoneBridge:
    """
    The Raspberry Bridge provides the protocol bridge between Xideco and a Raspberry Pi board using the
    pigpio library https://github.com/joan2937/pigpio

    """

    def __init__(self, board_num, board_type):
        """
        :param board_num: System Board Number (1-10)
        :param board_type: "black" or "green"
        :return:
        """
        self.board_num = board_num
        self.board_type = board_type.lower()

        self.payload = None
        self.black_gpio_pins = ["P9_11", "P9_12", "P9_13", "P9_14", "P9_15", "P9_16", "P9_17", "P9_18",
                                "P9_21", "P9_22", "P9_23", "P9_24", "P9_25", "P9_26", "P9_27", "P9_29",
                                "P9_30", "P9_31", "P9_41", "P9_42", "P8_7", "P8_8", "P8_9", "P8_10",
                                "P8_11", "P8_12", "P8_13", "P8_14", "P8_15", "P8_16", "P8_17", "P8_18",
                                "P8-19", "P8-26"]

        self.green_gpio_pins = ["P9_11", "P9_12", "P9_13", "P9_14", "P9_15", "P9_16", "P9_17", "P9_18",
                                "P9_21", "P9_22", "P9_23", "P9_24", "P9_25", "P9_26", "P9_27", "P9_29",
                                "P9_30", "P9_31", "P9_41", "P9_42", "P8_3", "P8_4", "P8_5", "P8_6",
                                "P8_7", "P8_8", "P8_9", "P8_10", "P8_11", "P8_12", "P8_13", "P8_14",
                                "P8_15", "P8_16", "P8_17", "P8_18", "P8_19", "P8_20", "P8_21", "P8_22",
                                "P8_23", "P8_24", "P8_25", "P8_26", "P8_27", "P8_28", "P8_29", "P8_30",
                                "P8_31", "P8_32", "P8_33", "P8_34", "P8_35", "P8_36", "P8_37", "P8_38",
                                "P8_39", "P8_40", "P8_41", "P8_42", "P8_43", "P8_44" "P8_45", "P8_46"]

        self.i2c_pins = {"scl": "P9_19", "sda": "P9_20"}

        self.analog_pins = ["P9_33", "P9_35", "P9_36", "P9_37", "P9_38", "P9_39", "P9_40"]

        self.pwm_pins = ["P9_14", "P9_16", "P9_21", "P9_22", "P9_29", "P9_31", "P9_42"]

        # this is a list of dictionary items describing a pin
        # each pin dictionary entry contains the pin id, its configured mode, and if it is enabled or not
        self.pins = []

        # set a list called pins to hold the pin modes
        for x in self.black_gpio_pins:
            entry = {'pin': x, 'mode': None, 'enabled': False}
            self.pins.append(entry)

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
        print('init done')

        print('a')

    def setup_analog_pin(self):
        """
        This method validates and configures a pin for analog input
        :return: None
        """
        # clear out any residual problem strings
        #

        self.last_problem = '2-0\n'

        print('called setup_analog_pin')

    def setup_digital_pin(self):
        """
        This method processes the Scratch "Digital Pin" Block that establishes the mode for the pin
        :return: None
        """

        # clear out any residual problem strings
        # self.report_problem('1-0\n')

        self.last_problem = '1-0\n'

        # retrieve mode from command
        mode = self.payload['mode']

        # Is the user enabling or disabling the pin? Get the 'raw' value and translate it.
        enable = self.payload['enable']

        if mode == 'SONAR':
            """
            pins = self.payload['pin'].split('.')
            self.payload['pin'] = pins[0]
            trigger_pin = self.validate_pin()
            if trigger_pin == 99:
                self.last_problem = '1-2\n'
                return

            self.payload['pin'] = pins[1]
            echo_pin = self.validate_pin()
            if echo_pin == 99:
                self.last_problem = '1-3\n'
                return

            if enable == 'Enable':
                self.enable_sonar(trigger_pin, echo_pin)
            else:
                self.disable_sonar()
            """
            pass

        else:

            pin = self.validate_pin()
            if pin == 99:
                self.last_problem = '1-1\n'
                return

            # retrieve mode from command
            mode = self.payload['mode']
            #
            if enable == 'Enable':
                # validate the mode for this pin
                if mode == 'Input':
                    """
                    self.pi.set_mode(pin, pigpio.INPUT)

                    # update the pin table
                    pin_entry = {'mode': pigpio.INPUT, 'enabled': True}
                    self.pins[pin] = pin_entry
                    self.pi.callback(pin, pigpio.EITHER_EDGE, self.cbf)
                """
                elif mode == 'Output':
                    index = self.black_gpio_pins.index(pin)
                    pin_entry = self.pins[index]

                    # update the pin table
                    # pin_entry = {'pin': pin, 'mode': GPIO.OUT, 'enabled': True}

                    GPIO.setup(pin, GPIO.OUT)
                    pin_entry['mode'] = GPIO.OUT
                    pin_entry['enabled'] = True

                    self.pins[index] = pin_entry
                    print('b')

                elif mode == 'PWM':
                    """
                    self.pi.set_mode(pin, pigpio.OUTPUT)

                    # update the pin table
                    pin_entry = {'mode': pigpio.OUTPUT, 'enabled': True}
                    self.pins[pin] = pin_entry
                    """
                    pass

                elif mode == 'Tone':
                    """
                    self.pi.set_mode(pin, pigpio.OUTPUT)

                    # update the pin table
                    pin_entry = {'mode': pigpio.OUTPUT, 'enabled': True}
                    self.pins[pin] = pin_entry
                    """
                    pass

                elif mode == 'Servo':
                    """
                    self.pi.set_mode(pin, pigpio.OUTPUT)
                    # update the pin table
                    pin_entry = {'mode': pigpio.OUTPUT, 'enabled': True}
                    self.pins[pin] = pin_entry
                    self.pi.set_mode(pin, pigpio.OUTPUT)
                    """
                    pass

            # must be disable
            else:
                index = self.black_gpio_pins.index(pin)
                pin_entry = self.pins[index]
                pin_entry['enabled'] = False
                self.pins[index] = pin_entry

                print('b')

    #
    def analog_write(self):
        """
        Set a PWM configured pin to the requested value
        :return: None
        """
        print('analog_write')
        pass
        """
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
        """

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
        index = self.black_gpio_pins.index(pin)
        pin_entry = self.pins[index]
        if pin_entry['mode'] != GPIO.OUT:
            self.last_problem = '3-2\n'
            return

        if not pin_entry['enabled']:
            self.last_problem = '3-3\n'
            return

        value = int(self.payload['value'])
        if value == 0:
            value = GPIO.LOW
        else:
            value = GPIO.HIGH

        GPIO.output(pin, value)


    def play_tone(self):
        """
        This method will play a tone using the Arduino tone library. It requires FirmataPlus
        :return: None
        """

        # clear out any residual problem strings

        self.last_problem = '5-0\n'

        """
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
        """

    def tone_off(self):

        pass
        """
        self.last_problem = '6-0\n'

        pin = self.validate_pin()
        if pin == 99:
            self.last_problem = '6-1\n'
            return

        self.pi.wave_tx_stop()  # stop waveform

        self.pi.wave_clear()  # clear all waveforms
        """

    def set_servo_position(self):
        pass

        """
        Set a servo position
       :return:
        """
        print('set_servo')

        """
        # time to allow servo to move
        delay = .6

        self.last_problem = '7-0\n'

        pin = self.validate_pin()
        if pin == 99:
            self.last_problem = '7-1\n'
            return

        # get pin information
        pin_state = self.pins[pin]
        if pin_state['mode'] != pigpio.OUTPUT:
            self.last_problem = '7-2\n'
            return

        position = int(self.payload['position'])

        # range of values for position is 500 to 2500
        # each degree is approximately equal to 11   (2000/180)
        # we add this to 500, the zero degree position
        position = (position * 11) + 500

        self.pi.set_servo_pulsewidth(pin, position)  # 0 degree
        # print("Servo {} {} micro pulses".format(str(servos), 500))
        time.sleep(delay)
        self.pi.set_servo_pulsewidth(pin, 0)
        """

    def validate_pin(self):
        pin = self.payload['pin']
        if self.board_type == 'black':
            if pin not in self.black_gpio_pins:
                return 99
            else:
                return self.payload['pin']
        else:
            print('validate pin: unknown board type: ' + self.board_type)

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

    def run_bb_bridge(self):
        print('run_bb')
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

    def cleanup(self):
        pass


def beaglebone_bridge():
    # noinspection PyShadowingNames

    parser = argparse.ArgumentParser()
    parser.add_argument("-b", dest="board_number", default="1", help="Board Number - 1 through 10")
    # parser.add_argument("-t", dest="board_type", default="black", help="black or green")


    args = parser.parse_args()

    board_num = args.board_number
    board_type = "black"
    bb_bridge = BeagleBoneBridge(board_num, board_type)
    try:
        bb_bridge.run_bb_bridge()
    except KeyboardInterrupt:
        bb_bridge.cleanup()
        sys.exit(0)

    # signal handler function called when Control-C occurs
    # noinspection PyShadowingNames,PyUnusedLocal,PyUnusedLocal
    def signal_handler(signal, frame):
        print("\nControl-C detected. See you soon.")
        sys.exit(0)

    # listen for SIGINT
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


if __name__ == "__main__":
    beaglebone_bridge()
