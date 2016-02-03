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
import socket
import sys
import time
import os

# noinspection PyPackageRequirements
import zmq

from xideco.data_files.port_map import port_map


class XidecoRouter:
    """
    This class consists of a PAIR connection to a control program bridge (i.e. - HTTP for Scratch),
    creates a publisher for Scratch commands, and creates a set of subscribers to listen
    for board data changes.
    """

    def __init__(self):
        """
        This is the constructor for the XidecoRouter class.
        :return: None
        """
        # figure out the IP address of the router
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # use the google dns
        s.connect(('8.8.8.8', 0))
        self.ip_addr = s.getsockname()[0]

        # identify the router ip address for the user on the console
        print('router IP address = ' + self.ip_addr)

        # find the path to the data files needed for operation
        path = sys.path

        self.base_path = None

        # get the prefix
        prefix = sys.prefix
        for p in path:
            # make sure the prefix is in the path to avoid false positives
            if prefix in p:
                # look for the configuration directory
                s_path = p + '/xideco/data_files/configuration'
                if os.path.isdir(s_path):
                    # found it, set the base path
                    self.base_path = p + '/xideco'
                    break

        if not self.base_path:
            print('Cannot locate xideco configuration directory.')
            sys.exit(0)

        print('\nport_map.py is located at:')
        print(self.base_path + '/data_files/port_map\n')

        print("Set router_ip_address in the port_map to the address printed above.")

        self.context = zmq.Context()

        # bind to the http server port
        self.http_socket = self.context.socket(zmq.PAIR)

        bind_string = "tcp://" + port_map.port_map['router_ip_address'] + ':' + port_map.port_map["http_port"]
        self.http_socket.bind(bind_string)
        self.payload = None

        # establish the command publisher - to the board bridges
        self.command_publisher_socket = self.context.socket(zmq.PUB)
        bind_string = "tcp://" + port_map.port_map['router_ip_address'] + ':' + port_map.port_map[
            'command_publisher_port']
        self.command_publisher_socket.bind(bind_string)

        # subscribe to report messages
        self.reporter_subscriber_socket = self.context.socket(zmq.SUB)
        bind_string = "tcp://" + port_map.port_map['router_ip_address'] + ':' + port_map.port_map[
            'reporter_publisher_port']
        self.reporter_subscriber_socket.bind(bind_string)

        for x in range(1, 11):
            env_string = "B" + str(x)
            envelope = env_string.encode()
            self.reporter_subscriber_socket.setsockopt(zmq.SUBSCRIBE, envelope)

    def route(self):
        """
        This method runs in a forever loop. It listens for commands on the PAIR and publishes them. It also
        listens for data updates for each board via subscription and forwards the updates via the PAIR
        :return:
        """
        while True:
            # see if there are any command messages from the http bridge
            try:
                [address, contents] = self.http_socket.recv_multipart(zmq.NOBLOCK)
                # x = umsgpack.unpackb(contents)
                # print("[%s] %s" % (address, x))
                self.command_publisher_socket.send_multipart([address, contents])
            except zmq.error.Again:
                pass
            except KeyboardInterrupt:
                sys.exit(0)

            # see if there are any reporter messages from the board bridges
            try:
                payload = self.reporter_subscriber_socket.recv_multipart(zmq.NOBLOCK)
                self.http_socket.send_multipart(payload)
            except zmq.error.Again:
                try:
                    time.sleep(.001)
                except KeyboardInterrupt:
                    sys.exit(0)

    def clean_up(self):
        self.http_socket.close()
        self.command_publisher_socket.close()
        self.reporter_subscriber_socket.close()
        self.context.term()


def xideco_router():
    # noinspection PyShadowingNames

    xideco_router = XidecoRouter()
    xideco_router.route()

    # signal handler function called when Control-C occurs
    # noinspection PyShadowingNames,PyUnusedLocal,PyUnusedLocal
    def signal_handler(signal, frame):
        print("Control-C detected. See you soon.")

        xideco_router.clean_up()

        sys.exit(0)

    # listen for SIGINT
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


# Instantiate the router and start the route loop
if __name__ == '__main__':
    xideco_router()
