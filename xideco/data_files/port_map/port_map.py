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

"""
This file contains a dictionary specifying various IP port numbers used with ZeroMQ sockets.
"""

# This map contains the ip address of the computer currently running the router.
# This address must be manually modified to match the IP address of the router computer.
# All other entries are fixed and should not be modifified.

# The publish_to_router_port should be used by all entities that wish to publish information.
# the subscribe_to_router_port should be used by all entities that with to subscribe to messages. The
# subscribers need to set a topic filter to receive the messages of interest.


port_map = {"router_ip_address": "192.168.2.192",
            "publish_to_router_port": "43124", "subscribe_to_router_port": "43125"}
