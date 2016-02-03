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

# The port selected for the aiohttp server running in the HTTP Bridge is
# fixed as 50208. Scratch does not allow dynamic port assignment.

port_map = {"router_ip_address": "192.168.2.101", "http_port": "43124", "command_publisher_port": "43125",
            "reporter_publisher_port": "43137",
            "1": "43127", "2": "43128", "3": "43129", "4": "43130", "5": "43131", "6": "43132",
            "7": "43133", "8": "43134", "9": "43135", "10": "43136"}
