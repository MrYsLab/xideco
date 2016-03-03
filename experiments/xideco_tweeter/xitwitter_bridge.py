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

import signal

import umsgpack
# noinspection PyPackageRequirements
import zmq
import time
import subprocess
import sys

from xideco.data_files.port_map import port_map


# noinspection PyMethodMayBeStatic,PyUnresolvedReferences,PyUnresolvedReferences,PyUnresolvedReferences
class TwitterBridge:
    """
    The Twitter Bridge provides the protocol bridge between Xideco and a Twitter generation request from Scratch
    """

    def __init__(self):
        """
        :param pymata_board: Pymata-aio instance
        :param board_num: Arduino Board Number (1-10)
        :return:
        """

        # establish the zeriomq sub and pub sockets
        self.context = zmq.Context()
        self.subscriber = self.context.socket(zmq.SUB)
        connect_string = "tcp://" + port_map.port_map['router_ip_address'] + ':' + port_map.port_map[
            'subscribe_to_router_port']
        self.subscriber.connect(connect_string)

        # create the topic we wish to subscribe to
        env_string = "A100" + self.board_num
        envelope = env_string.encode()
        self.subscriber.setsockopt(zmq.SUBSCRIBE, envelope)

        self.publisher = self.context.socket(zmq.PUB)
        connect_string = "tcp://" + port_map.port_map['router_ip_address'] + ':' + port_map.port_map[
            'publish_to_router_port']

        self.publisher.connect(connect_string)

        self.payload = ""

    def run_twitter_bridge(self):

        # noinspection PyBroadException
        try:
            msg = self.subscriber.recv_multipart(zmq.NOBLOCK)
            self.payload = umsgpack.unpackb(msg[1])
            print("[%s] %s" % (msg[0], self.payload))
            message = self.payload["message"]
            print(message)

            command = 'twitter -eMisterYsLab@gmail.com set %s' % message
            subprocess.call(command, shell=True)
            time.sleep(.001)
        except zmq.error.Again:
            time.sleep(.001)

    def clean_up(self):
        """
        Clean things up on exit
        :return:
        """
        self.subscriber.close()
        self.publisher.close()
        self.context.term()


def twitter_bridge():
    # noinspection PyShadowingNames

    # create an instance of the twitter bridge and then run it
    tbridge = TwitterBridge()
    while True:
        tbridge.run_twitter_bridge()

    # signal handler function called when Control-C occurs
    # noinspection PyShadowingNames,PyUnusedLocal,PyUnusedLocal
    def signal_handler(signal, frame):
        print("Control-C detected. See you soon.")

        tbridge.clean_up()

        sys.exit(0)

    # listen for SIGINT
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


if __name__ == "__main__":

    try:
        twitter_bridge()
    except KeyboardInterrupt:
        sys.exit(0)
