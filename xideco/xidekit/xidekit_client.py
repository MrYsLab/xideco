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

# noinspection PyPackageRequirements
import sys
import signal
from xideco.xidekit.xibase import XiBase


class Client(XiBase):
    def __init__(self, router_ip_address):
        super().__init__(router_ip_address)
        print('hello')


def client():
    """
    Main function for arduino bridge
    :return:
    """
    # noinspection PyShadowingNames

    # parser = argparse.ArgumentParser()
    # parser.add_argument('-r', dest='router_ip_address', default='None', help='Router IP Address')

    # args = parser.parse_args()

    # router_ip_address = args.router_ip_address

    application = Client('192.168.2.101')
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
    client()
