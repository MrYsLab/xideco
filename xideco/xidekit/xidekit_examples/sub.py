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
import sys

from xideco.xidekit.xidekit import XideKit


class MySub(XideKit):
    def __init__(self, router_ip_address=None, subscriber_port='43125', publisher_port='43124'):
        """
        For this example we simply call the __init__ of the super class.
        """
        super().__init__(router_ip_address, subscriber_port, publisher_port)

    def incoming_message_processing(self, topic, payload):
        """
        This method is overwritten in the inherited class to process the data
        :param topic: Message topic string
        :param payload: Message content
        :return:
        """
        print("Message From {0} : {1} \n".format(topic, payload['info']))


if __name__ == '__main__':
    try:
        my_sub = MySub()
        my_sub.set_subscriber_topic('p')
        my_sub.receive_loop()
    except KeyboardInterrupt:
        sys.exit(0)
