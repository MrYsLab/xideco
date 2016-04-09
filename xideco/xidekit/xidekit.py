"""
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

import socket
import sys
import time

import umsgpack
import zmq


# noinspection PyUnresolvedReferences
class XideKit:
    """

    This is a base class to be inherited by a derived Xideco application.

    To import use:

        from xideco.xidekit.xidekit import XideKit

    Methods that may be overwritten:  the __init__ method, the receive_loop and incoming_message_processing
    """

    def __init__(self, router_ip_address=None, subscriber_port='43125', publisher_port='43124'):
        """
        The __init__ method sets up all the ZeroMQ "plumbing"

        :param router_ip_address: Xideco Router IP Address - if not specified, it will be set to the local computer
        :param subscriber_port: Xideco router subscriber port. This must match that of the Xideco router
        :param publisher_port: Xideco router publisher port. This must match that of the Xideco router
        :return:
        """

        # If no router address was specified, determine the IP address of the local machine
        if router_ip_address:
            self.router_ip_address = router_ip_address
        else:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # use the google dns
            s.connect(('8.8.8.8', 0))
            self.router_ip_address = s.getsockname()[0]

        print('\n**************************************')
        print('Using router IP address: ' + self.router_ip_address)
        print('**************************************')

        self.subscriber_port = subscriber_port
        self.publisher_port = publisher_port

        # establish the zeriomq sub and pub sockets
        self.context = zmq.Context()
        self.subscriber = self.context.socket(zmq.SUB)
        connect_string = "tcp://" + self.router_ip_address + ':' + self.subscriber_port
        self.subscriber.connect(connect_string)

        self.publisher = self.context.socket(zmq.PUB)
        connect_string = "tcp://" + self.router_ip_address + ':' + self.publisher_port
        self.publisher.connect(connect_string)

    def set_subscriber_topic(self, topic):
        """
        This method sets the subscriber topic.

        You can subscribe to multiple topics by calling this method for
        each topic.
        :param topic: A topic string
        :return:
        """
        if not type(topic) is str:
            raise TypeError('Subscriber topic must be a string')

        self.subscriber.setsockopt(zmq.SUBSCRIBE, topic.encode())

    def publish_payload(self, payload, topic=''):
        """
        This method will publish a payload with the specified topic.

        :param payload: A dictionary of items
        :param topic: A string value
        :return:
        """
        if not type(topic) is str:
            raise TypeError('Publish topic must be a string', 'topic')

        if not type(payload) is dict:
            raise TypeError('Publish payload must be a dictionary', payload)

        # create a message pack payload
        message = umsgpack.packb(payload)

        pub_envelope = topic.encode()
        self.publisher.send_multipart([pub_envelope, message])

    def receive_loop(self):
        """
        This is the receive loop for zmq messages.

        It is assumed that this method will be overwritten to meet the needs of the application and to handle
        received messages.
        :return:
        """
        while True:
            try:
                data = self.subscriber.recv_multipart(zmq.NOBLOCK)
                self.incoming_message_processing(data[0].decode(), umsgpack.unpackb(data[1]))
                time.sleep(.001)
            except zmq.error.Again:
                time.sleep(.001)
            except KeyboardInterrupt:
                self.clean_up()

    # noinspection PyMethodMayBeStatic
    def incoming_message_processing(self, topic, payload):
        """
        Override this method with a message processor for the application

        :param topic: Message Topic string
        :param payload: Message Data
        :return:
        """
        print('this method should be overwritten in the child class', topic, payload)

    def clean_up(self):
        """
        Clean up before exiting - override if additional cleanup is necessary

        :return:
        """
        self.publisher.close()
        self.subscriber.close()
        self.context.term()
        sys.exit(0)



# this is a typical invocation of the class. The class is instantiated, topics are subscribed to, and
# the receive loop is started.
if __name__ == '__main__':
    a = XideKit()
    a.set_subscriber_topic('a')
    a.receive_loop()
