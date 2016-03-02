#!/usr/bin/env python2
"""
Created on February 16 08:48:15 2016

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
# noinspection PyPackageRequirements
import signal
import sys
import zmq
import umsgpack

from Adafruit_I2C import Adafruit_I2C


# noinspection PyMethodMayBeStatic,PyUnresolvedReferences,PyUnresolvedReferences,PyUnresolvedReferences
class BeagleBoneI2CBridge:
    """
    The Raspberry Bridge provides the protocol bridge between Xideco and a Raspberry Pi board using the
    pigpio library https://github.com/joan2937/pigpio

    """

    def __init__(self, board_num, router_ip_address, publisher_socket, subscriber_socket):
        """
        :param board_num: System Board Number (1-10)
        :param board_type: "black" or "green"
        :param servo_polarity: 1 or 0
        :return:
        """
        self.board_num = board_num
        if router_ip_address == 'None':
            print('You must use the -r command line option to specify the router IP Address')
            sys.exit(0)
        else:
            self.router_ip_address = router_ip_address

        self.publisher_socket = publisher_socket
        self.subscriber_socket = subscriber_socket

        print('\n*****************************************')
        print('BeagleBone Black i2c Interface - xibbi2c')
        print('Using router IP address: ' + self.router_ip_address)
        print('Publisher Socket: ' + self.publisher_socket)
        print('Subscriber Socket: ' + self.subscriber_socket)
        print('*****************************************')

        # establish the zeriomq sub and pub sockets
        self.context = zmq.Context()
        self.subscriber = self.context.socket(zmq.SUB)
        connect_string = "tcp://" + self.router_ip_address + ':' + self.subscriber_socket
        self.subscriber.connect(connect_string)

        # create the topic we wish to subscribe to
        env_string = "A" + self.board_num
        envelope = env_string.encode()
        self.subscriber.setsockopt(zmq.SUBSCRIBE, envelope)
        # subscribe to broadcast i2c message - i2c messages can also be board specific with A + board number
        self.subscriber.setsockopt(zmq.SUBSCRIBE, 'Q'.encode())

        self.publisher = self.context.socket(zmq.PUB)
        connect_string = "tcp://" + self.router_ip_address + ':' + self.publisher_socket

        self.publisher.connect(connect_string)

        # The Xideco protocol message received
        self.payload = None

        self.i2c_handle_dict = {}

    def i2c_request(self):
        cmd = self.payload['cmd']
        addr = self.payload['device_address']

        if cmd == 'init':
            handle = Adafruit_I2C(addr)
            self.i2c_handle_dict.update({addr: handle})
        elif cmd == 'write_byte':
            # get handle
            value = self.payload['value']
            handle = self.i2c_handle_dict[addr]
            register = self.payload['register']
            handle.write8(register, value)
        elif cmd == 'read_block':
            num_bytes = self.payload['num_bytes']
            handle = self.i2c_handle_dict[addr]
            register = self.payload['register']
            data = handle.readList(register, num_bytes)
            time.sleep(.0001)
            self.report_i2c_data(data)
        else:
            print('unknown cmd')

    def report_i2c_data(self, data):
        # create a topic specific to the board number of this board
        envelope = ("B" + self.board_num).encode()

        msg = umsgpack.packb({u"command": "i2c_reply", u"board": self.board_num, u"data": data})

        self.publisher.send_multipart([envelope, msg])

    def run_bb_i2c_bridge(self):
        """
        Start up the bridge
        :return:
        """
        # self.pi.set_mode(11, pigpio.INPUT)
        # cb1 = self.pi.callback(11, pigpio.EITHER_EDGE, self.cbf)
        while True:
            # noinspection PyBroadException
            try:
                z = self.subscriber.recv_multipart(zmq.NOBLOCK)
                self.payload = umsgpack.unpackb(z[1])
                # print("[%s] %s" % (z[0], self.payload))

                # print(self.payload)
                command = self.payload['command']
                if command == 'i2c_request':
                    self.i2c_request()
                else:
                    # print("can't execute unknown command'")
                    pass
                time.sleep(.0001)
            except KeyboardInterrupt:
                sys.exit(0)
            except zmq.error.Again:
                time.sleep(.0001)


def beaglebone_i2c_bridge():
    # noinspection PyShadowingNames

    parser = argparse.ArgumentParser()
    parser.add_argument("-b", dest="board_number", default="1", help="Board Number - 1 through 10")
    parser.add_argument("-p", dest="publisher_socket", default="43124", help="Publisher Socket Number")
    parser.add_argument("-s", dest="subscriber_socket", default="43125", help="Publisher Socket Number")
    parser.add_argument("-r", dest="router_ip_address", default="None", help="Router IP Address")

    args = parser.parse_args()

    board_num = args.board_number
    router_ip_address = args.router_ip_address
    publisher_socket = args.publisher_socket
    subscriber_socket = args.subscriber_socket

    bb_bridge = BeagleBoneI2CBridge(board_num, router_ip_address, publisher_socket,
                                    subscriber_socket)
    try:
        bb_bridge.run_bb_i2c_bridge()
    except KeyboardInterrupt:
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
    beaglebone_i2c_bridge()
