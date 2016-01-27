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

# import pigpio
import umsgpack
import Adafruit_BBIO.GPIO as GPIO

# noinspection PyPackageRequirements
import zmq
from xideco.data_files.port_map import port_map

import signal
import sys
import threading


# noinspection PyMethodMayBeStatic,PyUnresolvedReferences,PyUnresolvedReferences,PyUnresolvedReferences
class BeagleBoneBridge:
    """
    The Raspberry Bridge provides the protocol bridge between Xideco and a Raspberry Pi board using the
    pigpio library https://github.com/joan2937/pigpio

    """

    def __init__(self, board_num):
        """
        :param board_num: System Board Number (1-10)
        :return:
        """
        self.payload = None
        pass

    def run_bb_bridge(self):
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

    args = parser.parse_args()

    board_num = args.board_number
    bb_bridge = BeagleBoneBridge(board_num)
    # while True:
    # rpi_bridge.run_raspberry_bridge()
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
