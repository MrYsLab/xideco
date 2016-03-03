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

import pigpio
import umsgpack

# noinspection PyPackageRequirements
import zmq
from xideco.data_files.port_map import port_map

import signal
import sys
import threading


# noinspection PyMethodMayBeStatic,PyUnresolvedReferences,PyUnresolvedReferences,PyUnresolvedReferences
class RaspberryPiBridge:
    """
    The Raspberry Bridge provides the protocol bridge between Xideco and a Raspberry Pi board using the
    pigpio library https://github.com/joan2937/pigpio

    """

    def __init__(self, pi, board_num, router_ip_address):
        """
        :param pigpio: pigpio instance
        :param board_num: System Board Number (1-10)
        :return:
        """
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

        self.router_ip_address = router_ip_address

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

        if self.router_ip_address == 'None':
            self.router_ip_address = port_map.port_map['router_ip_address']
        else:
            self.router_ip_address = router_ip_address

        print('Xideco Raspberry Pi Bridge - xirp')
        print('\n**************************************')
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

        self.command_dict = {'digital_pin_mode': self.setup_digital_pin, 'digital_write': self.digital_write,
                             'analog_pin_mode': self.setup_analog_pin, 'analog_write': self.analog_write,
                             'set_servo_position': self.set_servo_position, 'play_tone': self.play_tone,
                             'tone_off': self.tone_off, 'i2c_request': self.i2c_request}

        self.last_problem = ''

        self.sonar = None
        self.a_to_d = None

        self.i2c_handle_dict = {}

    def setup_analog_pin(self):
        """
        This method validates and configures a pin for analog input
        :return: None
        """
        # clear out any residual problem strings
        #

        self.last_problem = '2-0\n'

        if not self.a_to_d:
            self.a_to_d = AtoD(self.pi, 1, 0x48, self.board_num)
            self.a_to_d.start()

        # test pin range 0-3

        pin = int(self.payload['pin'])
        if 0 <= pin <= 3:
            # check if enable or disable
            enable = self.payload['enable']
            if enable == 'Enable':
                self.a_to_d.set_report(pin, True)
            else:
                self.a_to_d.set_report(pin, False)

        else:
            self.last_problem = '2-1\n'

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

            # must be disable
            else:
                pin_entry = self.pins[pin]
                pin_entry['enabled'] = False
                self.pins[pin] = self.pin_entry

    def analog_write(self):
        """
        Set a PWM configured pin to the requested value
        :return: None
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

        if not (0 <= value <= 255):
            selt.last_problem = '4-4\n'
            return

        # self.board.digital_write(pin, value)
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
        This method will play a tone using a wave.
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
        time.sleep(delay)
        self.pi.set_servo_pulsewidth(pin, 0)

    def i2c_request(self):
        cmd = self.payload['cmd']
        addr = self.payload['device_address']

        if cmd == 'init':
            handle = self.pi.i2c_open(1, addr)
            self.i2c_handle_dict.update({addr: handle})
        elif cmd == 'write_byte':
            # get handle
            value = self.payload['value']
            handle = self.i2c_handle_dict[addr]
            register = self.payload['register']
            self.pi.i2c_write_byte_data(handle, register, value)
        elif cmd == 'read_block':
            num_bytes = self.payload['num_bytes']
            handle = self.i2c_handle_dict[addr]
            register = self.payload['register']
            data = self.pi.i2c_read_i2c_block_data(handle, register, num_bytes)
            self.report_i2c_data(data)
        else:
            print('unknown cmd')

    def report_i2c_data(self, data):
        # create a topic specific to the board number of this board
        envelope = ("B" + self.board_num).encode()

        # extract bytes from returned byte array and place in a list
        rdata = []
        for x in data[1]:
            rdata.append(x)

        msg = umsgpack.packb({u"command": "i2c_reply", u"board": self.board_num, u"data": rdata})

        self.publisher.send_multipart([envelope, msg])

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

    def enable_sonar(self, trigger, echo):
        self.sonar = Sonar(self.pi, trigger, echo, self.board_num)
        self.sonar.start()

    def disable_sonar(self):
        if self.sonar:
            self.sonar.cancel()

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

    # noinspection PyUnusedLocal
    def cbf(self, gpio, level, tick):
        """
        Gpio callback method to report changes
        :param gpio: pin
        :param level: value
        :param tick: time stamp
        :return:
        """

        # if the pin has reports disabled, just ignore
        pin_state = self.pins[gpio]

        # if user changes modes suppress output from being sent upstream
        if pin_state['mode'] == pigpio.OUTPUT:
            return
        digital_reply_msg = umsgpack.packb({u"command": "digital_read", u"pin": str(gpio), u"value": str(level)})

        envelope = ("B" + self.board_num).encode()
        self.publisher.send_multipart([envelope, digital_reply_msg])

    def cleanup(self):
        print('\nExiting...')
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


class Sonar(threading.Thread):
    """
    This class encapsulates a type of acoustic ranger.  In particular
    the type of ranger with separate trigger and echo pins.

    A pulse on the trigger initiates the sonar ping and shortly
    afterwards a sonar pulse is transmitted and the echo pin
    goes high.  The echo pins stays high until a sonar echo is
    received (or the response times-out).  The time between
    the high and low edges indicates the sonar round trip time.
    """

    def __init__(self, rpi, trigger, echo, board_num):
        """
        The class is instantiated with the Pi to use and the
        gpios connected to the trigger and echo pins.
        """
        super().__init__()
        self.pi = rpi
        self._trig = trigger
        # self._trig = 22
        self._echo = echo
        # self._echo = 9

        self.board_num = board_num

        self._ping = False
        self._high = None
        self._time = None

        self._triggered = False

        self._trig_mode = self.pi.get_mode(self._trig)
        self._echo_mode = self.pi.get_mode(self._echo)

        self.pi.set_mode(self._trig, pigpio.OUTPUT)
        self.pi.set_mode(self._echo, pigpio.INPUT)

        self._cb = self.pi.callback(self._trig, pigpio.EITHER_EDGE, self._cbf)
        self._cb = self.pi.callback(self._echo, pigpio.EITHER_EDGE, self._cbf)

        self.context = zmq.Context()

        self.publisher = self.context.socket(zmq.PUB)
        connect_string = "tcp://" + port_map.port_map['router_ip_address'] + ':' + port_map.port_map[
            'reporter_publisher_port']

        self.publisher.connect(connect_string)

        self._inited = True

    def _cbf(self, gpio, level, tick):
        """
        Callback from sonar data changes
        :param gpio: pin
        :param level: value
        :param tick: timestamp
        :return:
        """
        if gpio == self._trig:
            if level == 0:  # trigger sent
                self._triggered = True
                self._high = None
        else:
            if self._triggered:
                if level == 1:
                    self._high = tick
                else:
                    if self._high is not None:
                        self._time = tick - self._high
                        self._high = None
                        self._ping = True

    def read(self):
        """
        Triggers a reading.  The returned reading is the number
        of microseconds for the sonar round-trip.

        round trip cms = round trip time / 1000000.0 * 34030
        """
        if self._inited:
            try:
                self._ping = False
                self.pi.gpio_trigger(self._trig)
                start = time.time()
                while not self._ping:
                    if (time.time() - start) > 5.0:
                        return 20000
                    time.sleep(0.001)
                return self._time
            except AttributeError:
                sys.exit(0)
        else:
            return None

    def cancel(self):
        """
        Cancels the ranger and returns the gpios to their
        original mode.
        """
        if self._inited:
            self._inited = False
            self._cb.cancel()
            self.pi.set_mode(self._trig, self._trig_mode)
            self.pi.set_mode(self._echo, self._echo_mode)

    def run(self):
        """
        Retrieve sonar data and send report
        :return:
        """

        if not self._inited:
            self.cancel()

        end = time.time() + 600.0

        while time.time() < end:
            x = self.read()
            if x:
                # calculate round trip time
                x = x / 1000000.0 * 34030.0

                # calculate distance and round it off
                x /= 2
                x = round(x, 2)

                # publish the data

                digital_reply_msg = umsgpack.packb({u"command": "digital_read", u"pin": str(self._trig),
                                                    u"value": str(x)})

                envelope = ("B" + self.board_num).encode()
                self.publisher.send_multipart([envelope, digital_reply_msg])
                time.sleep(0.03)


class AtoD(threading.Thread):
    """
    This class handles the pcf8591 YL 40 Module analog to digital conversion module
    """

    def __init__(self, rpi, bus, address, board_num):
        """

        :param rpi: pigpio instance
        :param bus: i2c bus
        :param address: i2c address
        :return: nothing is returned
        """
        super().__init__()
        self.pi = rpi
        self.bus = bus
        self.address = address
        self.board_num = board_num

        self.handle = self.pi.i2c_open(self.bus, self.address)
        self.context = zmq.Context()

        self.publisher = self.context.socket(zmq.PUB)
        connect_string = "tcp://" + port_map.port_map['router_ip_address'] + ':' + port_map.port_map[
            'reporter_publisher_port']

        self.publisher.connect(connect_string)

        self.reports = [False, False, False, False]

    def set_report(self, index, value):
        """
        Set report table to send or deny reports
        :param index: pin number index into table
        :param value: True or False
        :return: nothing returned
        """
        self.reports[index] = value

    def run(self):
        """
        Continuously monitor the A/D
        :return:
        """
        a_out = 0
        while True:
            for a in range(0, 4):
                if self.reports[a]:
                    a_out += 1
                    self.pi.i2c_write_byte_data(self.handle, 0x40 | ((a + 1) & 0x03), a_out & 0xFF)
                    v = self.pi.i2c_read_byte(self.handle)
                    digital_reply_msg = umsgpack.packb({u"command": "analog_read", u"pin": str(a),
                                                        u"value": str(v)})
                    envelope = ("B" + self.board_num).encode()
                    self.publisher.send_multipart([envelope, digital_reply_msg])
            time.sleep(0.04)


def raspberrypi_bridge():
    """
    Main function for the raspberry pi bridge
    :return:
    """
    # noinspection PyShadowingNames

    parser = argparse.ArgumentParser()
    parser.add_argument("-b", dest="board_number", default="1", help="Board Number - 1 through 10")
    parser.add_argument('-r', dest='router_ip_address', default='None', help='Router IP Address')

    args = parser.parse_args()

    pi = pigpio.pi()

    board_num = args.board_number
    router_ip_address = args.router_ip_address
    rpi_bridge = RaspberryPiBridge(pi, board_num, router_ip_address)
    try:
        rpi_bridge.run_raspberry_bridge()
    except KeyboardInterrupt:
        rpi_bridge.cleanup()
        pi.stop()
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
    raspberrypi_bridge()
