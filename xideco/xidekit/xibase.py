#!/usr/bin/env python3
"""
Created on February 15 10:29:15 2016

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
import socket
import signal
import sys
import time

import umsgpack
# noinspection PyPackageRequirements
import zmq


# noinspection PyMethodMayBeStatic,PyUnresolvedReferences,PyUnresolvedReferences,PyUnresolvedReferences
class XiBase:
    """
    This is a base class on which Xideco modules may be based.
    """

    def __init__(self, router_ip_address):
        """
        :return:
        """
        if router_ip_address == 'None':

            # figure out the IP address of the this computer
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # use the google dns
            s.connect(('8.8.8.8', 0))
            self.router_ip_address = s.getsockname()[0]
        else:
            self.router_ip_address = router_ip_address

        print('\n**************************************')
        print('Using this router IP address: ' + self.router_ip_address)
        print('To specify some other address for the router, use the -r command line option')
        print('**************************************')

        self.port_map = {"publish_to_router_port": "43124", "subscribe_to_router_port": "43125"}

        # establish the zeriomq sub and pub sockets
        self.context = zmq.Context()
        self.subscriber = self.context.socket(zmq.SUB)
        connect_string = 'tcp://' + self.router_ip_address + ':' + self.port_map['subscribe_to_router_port']
        self.subscriber.connect(connect_string)

        # create the topic we wish to subscribe to
        env_string = 'A'
        envelope = env_string.encode()
        self.subscriber.setsockopt(zmq.SUBSCRIBE, envelope)

        self.publisher = self.context.socket(zmq.PUB)
        connect_string = 'tcp://' + self.router_ip_address + ':' + self.port_map['publish_to_router_port']

        self.publisher.connect(connect_string)

        # The Xideco protocol message received
        self.payload = None

    def publish(self, topic, message):

        """
        Publish the supplied Xideco protocol message
        :return:
        """
        envelope = (topic.encode())
        self.publisher.send_multipart([envelope, message])

    def subscribed_message_loop(self):
        while True:
            # noinspection PyBroadException
            try:
                z = self.subscriber.recv_multipart(zmq.NOBLOCK)
                self.payload = umsgpack.unpackb(z[1])
            except KeyboardInterrupt:
                self.cleanup()
                sys.exit(0)
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


def xibase():
    """
    Main function for arduino bridge
    :return:
    """
    # noinspection PyShadowingNames

    parser = argparse.ArgumentParser()
    parser.add_argument('-r', dest='router_ip_address', default='None', help='Router IP Address')

    args = parser.parse_args()

    router_ip_address = args.router_ip_address

    application = XiBase(router_ip_address)
    application.subscribed_message_loop()

    # signal handler function called when Control-C occurs
    # noinspection PyShadowingNames,PyUnusedLocal,PyUnusedLocal
    def signal_handler(signal, frame):
        print('Control-C detected. See you soon.')

        application.clean_up()

        sys.exit(0)

    # listen for SIGINT
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


if __name__ == "__main__":
    xibase()
