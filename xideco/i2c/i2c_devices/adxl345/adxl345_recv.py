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

# This is a sample program to monitor data being sent from adxl345.py using 'z' as the envelope.

# The router IP address is hardcoded as well as the port number
import umsgpack
import zmq
import time
import sys


context = zmq.Context()
subscriber = context.socket(zmq.SUB)
connect_string = 'tcp://192.168.2.192:43125'
subscriber.connect(connect_string)

env_string = 'z'
envelope = env_string.encode()
subscriber.setsockopt(zmq.SUBSCRIBE, envelope)

while True:
    try:
        msg = subscriber.recv_multipart(zmq.NOBLOCK)
        payload = umsgpack.unpackb(msg[1])
        print(payload)
    except KeyboardInterrupt:
        subscriber.close()
        context.term()
        sys.exit(0)
    except zmq.error.Again:
        time.sleep(.001)

