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
import os
import signal
import socket
import sys
import time

import zmq

from xideco.data_files.port_map import port_map


# noinspection PyUnresolvedReferences,PyUnresolvedReferences,PyUnresolvedReferences,PyUnresolvedReferences,PyUnresolvedReferences
class XidecoRouter:
    """
    This class consists of a PAIR connection to a control program bridge (i.e. - HTTP for Scratch),
    creates a publisher for Scratch commands, and creates a set of subscribers to listen
    for board data changes.
    """

    def __init__(self):
        """
        This is the constructor for the XidecoRouter class.
        :param: use_port_map: If true, use the ip address in the port map, if false, use discovered ip address
        :return: None
        """
        # figure out the IP address of the router
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # use the google dns
        s.connect(('8.8.8.8', 0))
        self.ip_addr = s.getsockname()[0]

        # identify the router ip address for the user on the console
        print('\nXideco Router - xirt')

        print('\n******************************************')
        print('Using router IP address = ' + self.ip_addr)
        print('******************************************')



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

        print('\nIf using the port map, port_map.py is located at:\n')
        print(self.base_path + '/data_files/port_map\n')

        print('NOTE: The path to port_map.py may be different')
        print('for each Operating System/Computer.')

        print('\nSet the router_ip_address entry in port_map.py ')
        print('to the address printed above for each ')
        print('computer running Xideco, or optionally ')
        print('set the address manually for each Xideco module')
        print('using the command line options.\n')

        self.router = zmq.Context()
        # establish router as a ZMQ FORWARDER Device

        # subscribe to any message that any entity publishes
        self.publish_to_router = self.router.socket(zmq.SUB)
        bind_string = 'tcp://' + self.ip_addr + ':' + port_map.port_map[
            'publish_to_router_port']
        self.publish_to_router.bind(bind_string)
        # Don't filter any incoming messages, just pass them through
        self.publish_to_router.setsockopt_string(zmq.SUBSCRIBE, '')

        # publish these messages
        self.subscribe_to_router = self.router.socket(zmq.PUB)
        bind_string = 'tcp://' + self.ip_addr + ':' + port_map.port_map[
            'subscribe_to_router_port']
        self.subscribe_to_router.bind(bind_string)

        zmq.device(zmq.FORWARDER, self.publish_to_router, self.subscribe_to_router)

    # noinspection PyMethodMayBeStatic
    def route(self):
        """
        This method runs in a forever loop.
        :return:
        """
        while True:
            try:
                time.sleep(.001)
            except KeyboardInterrupt:
                sys.exit(0)

    def clean_up(self):
        self.publish_to_router.close()
        self.subscribe_to_router.close()
        self.router.term()


def xideco_router():
    # noinspection PyShadowingNames

    xideco_router = XidecoRouter()
    xideco_router.route()

    # signal handler function called when Control-C occurs
    # noinspection PyShadowingNames,PyUnusedLocal,PyUnusedLocal
    def signal_handler(signal, frame):
        print('Control-C detected. See you soon.')

        xideco_router.clean_up()

        sys.exit(0)

    # listen for SIGINT
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


# Instantiate the router and start the route loop
if __name__ == '__main__':
    xideco_router()
