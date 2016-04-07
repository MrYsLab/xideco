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
import time
import sys

from xideco.xidekit.xidekit import XideKit

# create 2 publisher instances
my_pub1 = XideKit()
my_pub2 = XideKit()

# initialize the message
message = 0

# have both publishers send message with contents of the current message value
# send a message every quarter of a second
while True:
    try:
        my_pub1.publish_payload({'info': message}, 'p1')
        print("Message sent from my_pub1 = {0}   Message sent from my_pub2 = {1}\n".format(message, message+1))
        my_pub2.publish_payload({'info': message + 1}, 'p2')
        message += 2
        time.sleep(.25)
    except KeyboardInterrupt:
        sys.exit(0)

