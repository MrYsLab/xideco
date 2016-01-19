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
import atexit

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

        self.board_num = board_num
        self.pi = pi
        print("board num: " + board_num)
        hw_rev = self.pi.get_hardware_revision()
        print('HW REV: ' + str(hw_rev))

        pigpio_ver = self.pi.get_pigpio_version()
        print('PIGPIO REV: ' + str(pigpio_ver))

    def cbf(self, gpio, level, tick):
        print(gpio, level, tick)


    #     # lists of digital pin capabilities
    #     # These lists contain the pins numbers that support the capability
    #     self.input_capable = []
    #     self.output_capable = []
    #     self.analog_capable = []
    #     self.pwm_capable = []
    #     self.servo_capable = []
    #     self.i2c_capable = []
    #
    #     # a list to hold prepared problem msgpack messages
    #     self.problem_list = []
    #
    #     # this contains the numeric "A" (A0, A1..) channel values supported by the board
    #     self.analog_channel = []
    #
    #     # this is the total number of pins supported by the connected arduino
    #     self.num_digital_pins = 0
    #
    #     # for Snap - a dictionary of pins with their latest values
    #     self.digital_data = {}
    #     self.analog_data = {}
    #
    #     # go discover the type of Arduino that we are connected to
    #     self.get_pin_capabilities()
    #
    #     # establish the zeriomq sub and pub sockets
    #
    #     self.context = zmq.Context()
    #     self.subscriber = self.context.socket(zmq.SUB)
    #     connect_string = "tcp://" + port_map.port_map['router_ip_address'] + ':' + port_map.port_map[
    #         'command_publisher_port']
    #     self.subscriber.connect(connect_string)
    #
    #     # create the topic we wish to subscribe to
    #     env_string = "A" + self.board_num
    #     envelope = env_string.encode()
    #     self.subscriber.setsockopt(zmq.SUBSCRIBE, envelope)
    #
    #     self.publisher = self.context.socket(zmq.PUB)
    #     connect_string = "tcp://" + port_map.port_map['router_ip_address'] + ':' + port_map.port_map[
    #         'reporter_publisher_port']
    #
    #     self.publisher.connect(connect_string)
    #
    #     # The Xideco protocol message received
    #     self.payload = None
    #
    #     # "pointers" to the methods to process commands from the user
    #     self.command_dict = {'digital_pin_mode': self.setup_digital_pin, 'digital_write': self.digital_write,
    #                          'analog_pin_mode': self.setup_analog_pin, 'analog_write': self.analog_write,
    #                          'set_servo_position': self.set_servo_position, 'play_tone': self.play_tone,
    #                          'tone_off': self.tone_off}
    #
    #     # build all of the error messages ahead of time
    #     for x in range(0, 51):
    #         problem_string = str(x)
    #         self.problem_report = umsgpack.packb(
    #                 {u"command": "problem", u"board": board_num, u"problem": problem_string + '\n'})
    #         self.problem_list.append(self.problem_report)
    #
    # def setup_analog_pin(self):
    #     """
    #     This method validates and configures a pin for analog input
    #     :return: None
    #     """
    #     # clear out any residual problem strings
    #
    #     # print('called setup_analog_pin')
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
    # def setup_digital_pin(self):
    #     """
    #     This method processes the Scratch "Digital Pin" Block that establishes the mode for the pin
    #     :return: None
    #     """
    #
    #     # clear out any residual problem strings
    #     self.report_problem(self.problem_list[0])
    #
    #     # convert pin string to integer.
    #     try:
    #         pin = int(self.payload['pin'])
    #     except ValueError:
    #         # Pin Must Be Specified as an Integer 1-1
    #         self.report_problem(self.problem_list[1])
    #         return
    #
    #     # validate that the pin is within the pin count range
    #     # pin numbers start with 0 1-2
    #     if pin >= self.num_digital_pins:
    #         self.report_problem(self.problem_list[2])
    #         return
    #
    #     # Is the user enabling or disabling the pin? Get the 'raw' value and translate it.
    #     enable = self.payload['enable']
    #     # enable = self.check_cmd_enable_disable(enable)
    #     #
    #     # retrieve mode from command
    #     mode = self.payload['mode']
    #     # mode = self.check_cmd_digital_mode(mode)
    #     #
    #     if enable == 'Enable':
    #         # validate the mode for this pin
    #         if mode == 'Input':
    #             if pin in self.input_capable:
    #                 # send the pin mode to the arduino
    #                 self.board.set_pin_mode(pin, Constants.INPUT, self.digital_input_callback)
    #             else:
    #                 # this pin does not support input mode
    #                 self.report_problem(self.problem_list[3])
    #         # elif mode == 'Output':
    #         elif mode == 'Output':
    #             if pin in self.output_capable:
    #                 # send the pin mode to the arduino
    #                 self.board.set_pin_mode(int(pin), Constants.OUTPUT)
    #             else:
    #                 # this pin does not support output mode
    #                 self.report_problem(self.problem_list[4])
    #
    #         elif mode == 'PWM':
    #             if pin in self.pwm_capable:
    #                 # send the pin mode to the arduino
    #                 self.board.set_pin_mode(pin, Constants.PWM)
    #             else:
    #                 # this pin does not support output mode
    #                 self.report_problem(self.problem_list[5])
    #         elif mode == 'Servo':
    #             if pin in self.servo_capable:
    #                 # send the pin mode to the arduino
    #                 self.board.set_pin_mode(pin, Constants.SERVO)
    #             else:
    #                 # this pin does not support output mode
    #                 self.report_problem(self.problem_list[6])
    #         elif mode == 'Tone':
    #             if pin in self.servo_capable:
    #                 # send the pin mode to the arduino
    #                 self.board.set_pin_mode(pin, Constants.OUTPUT)
    #             else:
    #                 # this pin does not support output mode
    #                 self.report_problem(self.problem_list[7])
    #         elif mode == 'SONAR':
    #             if pin in self.input_capable:
    #                 # send the pin mode to the arduino
    #                 self.board.sonar_config(pin, pin, self.digital_input_callback, Constants.CB_TYPE_ASYNCIO)
    #             else:
    #                 # this pin does not support output mode
    #                 self.report_problem(self.problem_list[8])
    #         else:
    #             self.report_problem(self.problem_list[9])
    #     # must be disable
    #     else:
    #         pin_state = self.board.get_pin_state(pin)
    #         if pin_state[1] != Constants.INPUT:
    #             self.report_problem(self.problem_list[10])
    #         else:
    #             # disable the pin
    #             self.board.disable_digital_reporting(pin)
    #
    # def analog_write(self):
    #     """
    #     Set a PWM configured pin to the requested value
    #     :return: None
    #     """
    #
    #     self.report_problem(self.problem_list[0])
    #     # clear out any residual problem strings
    #
    #     try:
    #         pin = int(self.payload['pin'])
    #     except ValueError:
    #         # Pin Must Be Specified as an Integer
    #         self.report_problem(self.problem_list[16])
    #         return
    #
    #     pin_state = self.board.get_pin_state(pin)
    #     if len(pin_state) == 1:
    #         self.report_problem(self.problem_list[17])
    #         return
    #
    #     if pin_state[1] != Constants.PWM:
    #         self.report_problem(self.problem_list[18])
    #         return
    #
    #     try:
    #         value = int(self.payload['value'])
    #     except ValueError:
    #         # Pin Must Be Specified as an Integer
    #         self.report_problem(self.problem_list[19])
    #         return
    #
    #     # validate range of value
    #     if 0 <= value <= 255:
    #         self.board.analog_write(pin, value)
    #     else:
    #         self.report_problem(self.problem_list[20])
    #
    # def digital_write(self):
    #     """
    #     Set the state of a digital pin
    #     :return:
    #     """
    #
    #     # clear out any residual problem strings
    #     self.report_problem(self.problem_list[0])
    #
    #     try:
    #         pin = int(self.payload['pin'])
    #     except ValueError:
    #         self.report_problem(self.problem_list[13])
    #         return
    #
    #     pin_state = self.board.get_pin_state(pin)
    #     if len(pin_state) == 1:
    #         self.report_problem(self.problem_list[14])
    #         return
    #
    #     if pin_state[1] != Constants.OUTPUT:
    #         self.report_problem(self.problem_list[15])
    #         return
    #
    #     value = int(self.payload['value'])
    #     self.board.digital_write(pin, value)
    #
    # def play_tone(self):
    #     """
    #     This method will play a tone using the Arduino tone library. It requires FirmataPlus
    #     :return: None
    #     """
    #     # clear out any residual problem strings
    #     self.report_problem(self.problem_list[0])
    #     # get the pin string from the block
    #     try:
    #         pin = int(self.payload['pin'])
    #     except ValueError:
    #         # Pin Must Be Specified as an Integer
    #         self.report_problem(self.problem_list[21])
    #         return
    #
    #     pin_state = self.board.get_pin_state(pin)
    #     if len(pin_state) == 1:
    #         self.report_problem(self.problem_list[22])
    #         return
    #
    #     if pin_state[1] != Constants.OUTPUT:
    #         self.report_problem(self.problem_list[23])
    #         return
    #
    #     frequency = self.payload['frequency']
    #
    #     try:
    #         frequency = int(frequency)
    #     except ValueError:
    #         # frequency Must Be Specified as an Integer
    #         self.report_problem(self.problem_list[24])
    #         return
    #
    #     try:
    #         duration = int(self.payload['duration'])
    #     except ValueError:
    #         # frequency Must Be Specified as an Integer
    #         self.report_problem(self.problem_list[25])
    #         return
    #
    #     self.board.play_tone(pin, Constants.TONE_TONE, frequency, duration)
    #
    # def tone_off(self):
    #     """
    #     Turn tone off
    #     :return:
    #     """
    #     # clear out any residual problem strings
    #     self.report_problem(self.problem_list[0])
    #     # get the pin string from the block
    #     try:
    #         pin = int(self.payload['pin'])
    #     except ValueError:
    #         # Pin Must Be Specified as an Integer
    #         self.report_problem(self.problem_list[26])
    #         return
    #
    #     pin_state = self.board.get_pin_state(pin)
    #     if len(pin_state) == 1:
    #         self.report_problem(self.problem_list[27])
    #         return
    #
    #     if pin_state[1] != Constants.OUTPUT:
    #         self.report_problem(self.problem_list[28])
    #         return
    #
    #     self.board.play_tone(pin, Constants.TONE_NO_TONE, None, None)
    #     return
    #
    # def set_servo_position(self):
    #     """
    #     Set a servo position
    #     :return:
    #     """
    #     # clear out any residual problem strings
    #     self.report_problem(self.problem_list[0])
    #
    #     try:
    #         pin = int(self.payload['pin'])
    #     except ValueError:
    #         self.report_problem(self.problem_list[29])
    #         return
    #
    #     pin_state = self.board.get_pin_state(pin)
    #     if len(pin_state) == 1:
    #         self.set_problem(self.problem_list[30])
    #         return
    #
    #     if pin_state[1] != Constants.SERVO:
    #         self.set_problem(self.problem_list[31])
    #         return
    #
    #     position = self.payload['position']
    #
    #     try:
    #         position = int(position)
    #     except ValueError:
    #         # frequency Must Be Specified as an Integer
    #         self.set_problem(self.problem_list[32])
    #         return
    #
    #     if 0 <= position <= 180:
    #         self.board.analog_write(pin, position)
    #     else:
    #         self.set_problem(self.problem_list[33])
    #     return
    #
    # def digital_input_callback(self, data):
    #     """
    #     This method receives digital data inputs, creates a Xideco protocol publishing message and publishes the message
    #     :param data: data[0] = pin, data[1] = value
    #     :return: None
    #     """
    #     pin = str(data[0])
    #     value = str(data[1])
    #
    #     digital_reply_msg = umsgpack.packb({u"command": "digital_read", u"pin": pin, u"value": value})
    #
    #     envelope = ("B" + self.board_num).encode()
    #     self.publisher.send_multipart([envelope, digital_reply_msg])
    #     # print(digital_reply_msg)
    #     # print(envelope)
    #
    # def analog_input_callback(self, data):
    #     """
    #     This method receives Analog data inputs, creates a Xideco protocol publishing message and publishes the message
    #     :param data: data[0] = pin, data[1] = value
    #     :return: None
    #     """
    #     pin = str(data[0])
    #     value = str(data[1])
    #
    #     analog_reply_msg = umsgpack.packb({u"command": "analog_read", u"pin": pin, u"value": value})
    #
    #     envelope = ("B" + self.board_num).encode()
    #     self.publisher.send_multipart([envelope, analog_reply_msg])
    #
    def run_raspberry_bridge(self):
        self.pi.set_mode( 11, pigpio.INPUT)
        cb1 = self.pi.callback(11, pigpio.EITHER_EDGE, self.cbf)
        while True:
            pass



        # noinspection PyBroadException
        # try:
        #     z = self.subscriber.recv_multipart(zmq.NOBLOCK)
        #     self.payload = umsgpack.unpackb(z[1])
        #     print("[%s] %s" % (z[0], self.payload))
        #     command = self.payload['command']
        #     if command in self.command_dict:
        #         self.command_dict[command]()
        #     else:
        #         print("can't execute unknown command'")
        #     self.board.sleep(.001)
        # except:
        #     self.board.sleep(.001)
        #     return
    #
    # def get_pin_capabilities(self):
    #     """
    #     This method retrieves the Arduino pin capability and analog map reports.
    #     For each digital pin mode, a list of valid pins is constructed,
    #     A total pin count is calculated and in addition,
    #     a list of valid analog input channels is constructed.
    #     :return: None
    #     """
    #     # get the capability report
    #     pin_capabilities = self.board.get_capability_report()
    #
    #     # initialize the total pin count to o
    #     pin_count = 0
    #
    #     pin_data = []
    #
    #     # Each set of digital pin capabilities is delimited by the value of 127
    #     # Accumulate all of the capabilities into a list for the current pin
    #     for x in pin_capabilities:
    #         if x != 127:
    #             pin_data.append(x)
    #             continue
    #         # Found a delimiter, populate the specific capability lists with this pin.
    #         # Each capability contains 2 bytes. The first is the capability and the second is the
    #         # number of bits of data resolution for the pin. The resolution is ignored
    #         else:
    #             pin__x_capabilities = pin_data[::2]
    #             for y in pin__x_capabilities:
    #                 if y == 0:
    #                     self.input_capable.append(pin_count)
    #                 elif y == 1:
    #                     self.output_capable.append(pin_count)
    #                 elif y == 2:
    #                     self.analog_capable.append(pin_count)
    #                 elif y == 3:
    #                     self.pwm_capable.append(pin_count)
    #                 elif y == 4:
    #                     self.servo_capable.append(pin_count)
    #                 elif y == 6:
    #                     self.i2c_capable.append(pin_count)
    #                 else:
    #                     print('Unknown Pin Type ' + y)
    #             # clear the pin_data list for the next pin and bump up the pin count
    #             pin_data = []
    #             # add an entry into the digital data dictionary
    #             self.digital_data[pin_count] = 0
    #
    #             pin_count += 1
    #     # Done with digital pin discovery, save the pin count
    #     self.num_digital_pins = pin_count
    #
    #     # Get analog channel data and create the analog_channel list
    #     analog_pins = self.board.get_analog_map()
    #     for x in analog_pins:
    #         if x != 127:
    #             self.analog_channel.append(x)
    #             self.analog_data[x] = 0
    #
    # def report_problem(self, problem):
    #     """
    #     Publish the supplied Xideco protocol message
    #     :param problem: problem report
    #     :return:
    #     """
    #     # create a topic specific to the board number of this board
    #     envelope = ("B" + self.board_num).encode()
    #     self.publisher.send_multipart([envelope, problem])

    def cleanup(self):
        print('cleaning up')
        self.pi.stop()




def raspberrypi_bridge():
    # noinspection PyShadowingNames

    parser = argparse.ArgumentParser()
    parser.add_argument("-b", dest="board_number", default="1", help="Board Number - 1 through 10")
    # parser.add_argument("-p", dest="comport", default="None", help="Arduino COM port - e.g. /dev/ttyACMO or COM3")

    args = parser.parse_args()

    pi = pigpio.pi()

    board_num = args.board_number
    rbridge = RaspberryPiBridge(pi, board_num)
    #while True:
        #rbridge.run_raspberry_bridge()
    try:
        rbridge.run_raspberry_bridge()
    except:
        print('done done')
        rbridge.cleanup()
        # pi.stop()
        sys.exit(0)




    # signal handler function called when Control-C occurs
    # noinspection PyShadowingNames,PyUnusedLocal,PyUnusedLocal
    def signal_handler(signal, frame):
        print("Control-C detected. See you soon.")
        time.sleep(5)
    #
        rbridge.clean_up()
    #
        # sys.exit(0)
    #
    # listen for SIGINT
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


if __name__ == "__main__":
    # try:
        raspberrypi_bridge()
    # except KeyboardInterrupt:
    #     sys.exit(0)
