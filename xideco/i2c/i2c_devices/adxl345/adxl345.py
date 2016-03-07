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
import math
import sys
import threading
import time

import umsgpack
# noinspection PyPackageRequirements
import zmq
from xideco.data_files.port_map import port_map


# noinspection PyMethodMayBeStatic,PyUnresolvedReferences,PyUnresolvedReferences,PyUnresolvedReferences,PyShadowingNames
class ADXL345(threading.Thread):
    """
        This class allows control and monitoring of the ADXL345 Accelerometer. It is a Xideco Universal i2c
        implementation that will allow use of the ADXL345 on Arduino, Raspberry Pi, and BeagleBone MCUs.
        Range is set to 16 g.

        It uses a separate thread to affect continuous reading.

        At the bottom of this file is a demo program of its use.

        Import this module into your application  and then instantiate to use.

        This module will report:
            board number
            raw x,y,z values
            accelerometer values for x,y,z expressed in g's
            normalized value for x,y,z
            pitch and roll angles
        """

    # This is the pseudo board number indicating that the commands are broadcast to all connectedADXL345
    # simultaneously
    BROADCAST = 5000

    # report data formats
    RAW = 0

    def __init__(self, router_ip_address, board_number=BROADCAST, data_publish_envelope=None):
        """
        :param router_ip_address: IP Address of router
        :param board_number: Board number or BROADCAST to send to all boards
        :param: publish_envelope: Set this parameter to publish data using the user specified envelope
        :return:
        """
        # call the parent class init and set the thread as a daemon thread
        super().__init__()
        self.daemon = True

        # router IP address
        self.board_number = board_number
        self.data_publish_envelope = data_publish_envelope
        self.read_time = None

        # A parameter is provided by the user to force the router ip address instead of reading from the
        # configuration file.

        # if not specified, the router ip address is read from the configuration file
        if router_ip_address == 'None':
            self.router_ip_address = port_map.port_map['router_ip_address']
        else:
            self.router_ip_address = router_ip_address

        print('\n************************************************************')
        print('ADXL345')
        print('Using this router IP address: ' + self.router_ip_address)
        print('************************************************************')

        # establish the zeriomq subscriber socket
        self.context = zmq.Context()
        self.subscriber = self.context.socket(zmq.SUB)
        connect_string = 'tcp://' + self.router_ip_address + ':' + port_map.port_map['subscribe_to_router_port']
        self.subscriber.connect(connect_string)

        # create the topic we wish to subscribe to - we will accept messages from all boards without regard to
        # board number. The reported data will contain the board number being reported
        env_string = 'B'
        envelope = env_string.encode()
        self.subscriber.setsockopt(zmq.SUBSCRIBE, envelope)

        # create the zeromq publisher socket
        self.publisher = self.context.socket(zmq.PUB)
        connect_string = 'tcp://' + self.router_ip_address + ':' + port_map.port_map['publish_to_router_port']
        self.publisher.connect(connect_string)

        # Published message topics - either a Q for broadcast or A + board number for individual boards
        if board_number < self.BROADCAST:
            self.publish_envelope = ("A" + str(board_number)).encode()
        else:
            self.publish_envelope = ("Q".encode())

        # The Xideco protocol message received
        self.payload = None

        # user callback method called to optionally report data
        self.callback = None

        # a flag that the user can set via start_continuous and stop_continuous to affect continuous reading of data
        self.keep_reading = True

        # the last read is stored here and can be retrieved by a call to get_last_data
        self.last_data = {'board': 0, 'x_raw': 0, 'y_raw': 0, 'z_raw': 0,
                          'x_g': 0.0, 'y_g': 0.0, 'z_g': 0.0,
                          'x_a': 0.0, 'y_a': 0.0, 'z_a': 0.0,
                          'pitch': 0.0, 'roll': 0.0}

        # this is the device i2c xideco operations descriptor

        # initialization:
        #   Send and "init" instruction
        #   Set the Power Control Register to 0
        #   Set the Power Control Register to 8 = Measure Bit enabled
        #   Set the Data Format Register to 8 for full resolution
        #   set the Data Format Resister to 3 - 10 bit resolution and 16 g range

        # read
        #   Retrieve 6 bytes from the Data Register

        self.i2c_device = {
            "adxl345": {
                "device_address": 83,
                "commands": {
                    "init": [
                        {
                            u"cmd": u"init",
                        },
                        {
                            u"cmd": u"write_byte",
                            u"register": 45,
                            u"value": 0
                        }, {
                            u"cmd": u"write_byte",
                            u"register": 45,
                            u"value": 8
                        }, {
                            u"cmd": u"write_byte",
                            u"register": 49,
                            u"value": 8
                        },
                        {
                            u"cmd": u"write_byte",
                            u"register": 49,
                            u"value": 3
                        }
                    ],
                    "read": [{
                        u"cmd": "read_block",
                        u"register": 50,
                        u"num_bytes": 6
                    }]
                }
            }
        }

    def initialize_device(self, callback=None):
        """
        This method sends out the i2c initialization sequence to the MCUs. If a callback is specified, all
        data will be reported via the callback, as well as stored internally to allow polling.
        :param callback: Optional callback function provided by user
        :return:
        """
        if callback:
            self.callback = callback
        msg = self.i2c_device['adxl345']['commands']['init']
        self._send_to_device(msg)

    def read_device(self):
        """
        Force a one-shot read of the device
        :return: Return the last set of values read
        """
        msg = self.i2c_device['adxl345']['commands']['read']
        self._send_to_device(msg)
        self._process_subscribed_message()
        return self.last_data

    def start_continuous(self, read_time=None):
        """
        Start a continuous read. Create the read thread if not already created.
        If read time is None, time period between read is .001 seconds
        :param read_time: Amount of time to delay after receiving data back from device
        :return:
        """
        self.keep_reading = True
        self.read_time = read_time

        # start the thread if it is not running already
        if not self.is_alive():
            self.start()

    def stop_continuous(self):
        """
        This function halts the automatic read and reporting of the device
        :return:
        """
        self.keep_reading = False

    def get_last_data(self):
        """
        This method retrieves the data retrieved from the last read - continuous or manual
        :return:
        """
        return self.last_data

    def _send_to_device(self, msg):
        """
        Send a control messages to the device
        :param msg: A list of messages to be sent as specified by i2c_device
        :return:
        """
        address = self.i2c_device['adxl345']['device_address']

        for i in msg:
            i.update({u"command": u"i2c_request"})
            i.update({u"device_address": address})

            msg = umsgpack.packb(i)
            time.sleep(.001)
            self.publisher.send_multipart([self.publish_envelope, msg])

    def _process_subscribed_message(self):
        """
        Wait for data to be returned by the i2c device.
        It stores the data in last_data, and calls the callback if one was specified when the device was initialized.
        :return:
        """
        # noinspection PyPep8Naming
        EARTH_GRAVITY_MS2 = 9.80665

        while True:
            if self.keep_reading:
                # noinspection PyBroadException
                try:
                    msg = self.subscriber.recv_multipart(zmq.NOBLOCK)
                    # extract board number from envelope
                    board = msg[0].decode()
                    board = int(board[1:])
                    self.payload = umsgpack.unpackb(msg[1])

                    if not 'data' in self.payload:
                        continue
                    raw = self.payload['data']

                    # mask off bits not being used
                    raw[1] &= 0x3
                    raw[3] &= 0x3
                    raw[5] &= 0x3

                    # get raw value for x
                    x = raw[0] | (raw[1] << 8)
                    x = self._twos_comp(x, 10)
                    x = round(x, 4)

                    # express x in g forces
                    xg = x * .004
                    xg = round(xg, 4)

                    # express x as a normalized acceleration
                    xa = xg * EARTH_GRAVITY_MS2
                    xa = round(xa, 4)

                    # get raw value for y
                    y = raw[2] | (raw[3] << 8)
                    y = self._twos_comp(y, 10)
                    y = round(y, 4)

                    # express y in g forces
                    yg = y * .004
                    yg = round(yg, 4)

                    # express y as a normalized acceleration
                    ya = yg * EARTH_GRAVITY_MS2
                    ya = round(ya, 4)

                    # get raw value for z
                    z = raw[4] | (raw[5] << 8)
                    z = self._twos_comp(z, 10)
                    z = round(z, 4)

                    # express z in g forces
                    zg = z * .004
                    zg = round(zg, 4)

                    # express z as a normalized acceleration
                    za = zg * EARTH_GRAVITY_MS2
                    za = round(za, 4)

                    pitch = int(-(math.atan2(xa, math.sqrt(ya * ya + za * za)) * 180.0) / math.pi)

                    roll = int((math.atan2(ya, za) * 180.0) / math.pi)

                    self.last_data[u'x_raw'] = x
                    self.last_data[u'y_raw'] = y
                    self.last_data[u'z_raw'] = z

                    self.last_data[u'x_g'] = xg
                    self.last_data[u'y_g'] = yg
                    self.last_data[u'z_g'] = zg

                    self.last_data[u'x_a'] = xa
                    self.last_data[u'y_a'] = ya
                    self.last_data[u'z_a'] = za

                    self.last_data[u'roll'] = roll
                    self.last_data[u'pitch'] = pitch

                    self.last_data[u'board'] = board

                    # if there is a callback registered, call it
                    if self.callback:
                        self.callback(self.last_data)

                    # if there is a publisher envelope, publish the data
                    if self.data_publish_envelope:
                        data_publish_envelope = (self.data_publish_envelope.encode())

                        msg = umsgpack.packb(self.last_data)
                        time.sleep(.001)
                        self.publisher.send_multipart([data_publish_envelope, msg])
                        time.sleep(.001)

                    return
                except KeyboardInterrupt:
                    self.clean_up()
                    sys.exit(0)
                except zmq.error.Again:
                    time.sleep(.001)
            else:
                time.sleep(.001)
                pass

    def _twos_comp(self, val, bits):
        if (val & (1 << (bits - 1))) != 0:
            val -= 1 << bits
        return val

    def clean_up(self):
        """
        Clean things up on exit
        :return:
        """
        self.subscriber.close()
        self.publisher.close()
        self.context.term()

    def run(self):
        while True:
            try:
                msg = self.i2c_device['adxl345']['commands']['read']
                self._send_to_device(msg)
                self._process_subscribed_message()
                if self.read_time:
                    time.sleep(self.read_time)
            except KeyboardInterrupt:
                self.clean_up()
                sys.exit()
            except SystemExit:
                self.clean_up()
                sys.exit()


# a sample callback routine
def data_callback(data):
    p = data['pitch']
    r = data['roll']
    print('Pitch: {0}, Roll: {1}.'.format(p, r))
    # print('Pitch: {0}, Roll: {1}.'.format(r, p))
    # print(data['x_raw'], data['y_raw'], data['z_raw'])
    # print(data['x_a'], data['y_a'], data['z_a'])


def adxl345(router_address):
    # instantiate the device forcing the routing IP address and setting the data publisher envelope to 'z'
    device = ADXL345(router_address, data_publish_envelope='z')

    try:

        # poll data for 10 iterations
        print("polling 10 times")

        # first initialize the device
        device.initialize_device()

        # now poll ten times and print to the console
        for x in range(0, 10):
            device.read_device()
            print(device.get_last_data())

        print("continuous callback for 3 seconds")

        # to run continuous, initialize the device specifying a call back function
        device.initialize_device(data_callback)

        # start continuous operation with a delay after data reported of .001 seconds
        device.start_continuous(.001)

        time.sleep(3)

        # we can halt the continuous operation by calling stop_continuous
        print('halting for 3 seconds')
        device.stop_continuous()
        time.sleep(3)

        # We can re-enable by calling start_continuous
        print('enabling continuous for 3 seconds')
        device.start_continuous(.001)
        time.sleep(3)

        # Halt and then read the last data reported
        print('halting and reading the last value reported then wait 2 seconds')
        device.stop_continuous()
        print(device.get_last_data())
        time.sleep(2)

        # we are out of here
        print('exiting')
        device.clean_up()
        sys.exit(0)
    except KeyboardInterrupt:
        device.clean_up()
        sys.exit(0)


if __name__ == "__main__":
    adxl345("192.163.2.193")
