#!/usr/bin/env python3
"""
Created on January 2 11:39:15 2016

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
import asyncio
import configparser
import os
import signal
import sys
import umsgpack

from aiohttp import web
# noinspection PyPackageRequirements
import zmq
from xideco.data_files.port_map import port_map


# noinspection PyUnresolvedReferences,PyUnresolvedReferences,PyUnresolvedReferences
class HttpBridge:
    """
    This is an HTTP bridge that translates Scratch HTTP requests into xideco protocol messages
   """

    def __init__(self, router_ip_address=None):
        """
        This is the constructor for the xideco HTTP bridge
        :return:
        """

        # find the path to the data files needed for operation
        path = sys.path

        self.base_path = None

        self.router_ip_address = router_ip_address

        # establish the zeriomq sub and pub sockets

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

        if self.router_ip_address == 'None':
            self.router_ip_address = port_map.port_map['router_ip_address']
        else:
            self.router_ip_address = router_ip_address

        print('\n**************************************')
        print('Scratch HTTP Bridge - xihb')
        print('Using router IP address: ' + self.router_ip_address)
        print('**************************************')

        print('\nTo specify some other address for the router, use the -r command line option')

        print('\nScratch Project Files Located at:')
        print(self.base_path + '/data_files/scratch_files/projects\n')
        print('port_map.py is located at:')
        print(self.base_path + '/data_files/port_map\n')

        # Scratch poll reply string
        self.poll_reply = ""

        # grab the config file and get it ready for parsing
        config = configparser.ConfigParser()
        config_file_path = str(self.base_path + '/data_files/configuration/configuration.cfg')
        config.read(config_file_path, encoding="utf8")

        # parse the file and place the translation information into the appropriate variable
        self.ln_languages = config.get('translation_lists', 'ln_languages').split(',')
        self.ln_ENABLE = config.get('translation_lists', 'ln_ENABLE').split(',')
        self.ln_DISABLE = config.get('translation_lists', 'ln_DISABLE').split(',')
        self.ln_INPUT = config.get('translation_lists', 'ln_INPUT').split(',')
        self.ln_OUTPUT = config.get('translation_lists', 'ln_OUTPUT').split(',')
        self.ln_PWM = config.get('translation_lists', 'ln_PWM').split(',')
        self.ln_SERVO = config.get('translation_lists', 'ln_SERVO').split(',')
        self.ln_TONE = config.get('translation_lists', 'ln_TONE').split(',')
        self.ln_SONAR = config.get('translation_lists', 'ln_SONAR').split(',')
        self.ln_OFF = config.get('translation_lists', 'ln_OFF').split(',')
        self.ln_ON = config.get('translation_lists', 'ln_ON').split(',')

    # noinspection PyShadowingNames,PyAttributeOutsideInit,PyAttributeOutsideInit,PyUnresolvedReferences
    async def init(self, loop):
        """
        This method initializes the aiohttp server.
        It also instantiate all of the s2aio servers specified in the configuration file.
        After the servers are initialized, the "poll" command is added to the aiohttp server, so that the
        "green" Scratch connectivity indicator stays red until after the servers are instantiated.
        :param loop: asyncio event loop
        :return: http server instance
        """

        app = web.Application(loop=loop)

        app.router.add_route('GET', '/digital_pin_mode/{board}/{enable}/{pin}/{mode}', self.setup_digital_pin)
        app.router.add_route('GET', '/analog_pin_mode/{board}/{enable}/{pin}', self.setup_analog_pin)
        app.router.add_route('GET', '/digital_write/{board}/{pin}/{value}', self.digital_write)
        app.router.add_route('GET', '/analog_write/{board}/{pin}/{value}', self.analog_write)
        app.router.add_route('Get', '/analog_read/{board}/{pin}/{value}', self.got_analog_report)
        app.router.add_route('Get', '/digital_read/{board}/{pin}/{value}', self.got_digital_report)
        app.router.add_route('GET', '/play_tone/{board}/{pin}/{frequency}/{duration}', self.play_tone)

        app.router.add_route('Get', '/problem/{board}/{problem}', self.got_problem_report)
        app.router.add_route('GET', '/set_servo_position/{board}/{pin}/{position}', self.set_servo_position)
        app.router.add_route('GET', '/tone_off/{board}/{pin}', self.tone_off)

        srv = await loop.create_server(app.make_handler(), '127.0.0.1', 50208)
        self.loop = loop

        self.context = zmq.Context()
        self.subscriber = self.context.socket(zmq.SUB)
        connect_string = "tcp://" + self.router_ip_address + ':' + port_map.port_map[
            'subscribe_to_router_port']
        self.subscriber.connect(connect_string)

        # create the topics we wish to subscribe to
        for x in range(1, 11):
            env_string = "B" + str(x)
            envelope = env_string.encode()
            self.subscriber.setsockopt(zmq.SUBSCRIBE, envelope)

        self.publisher = self.context.socket(zmq.PUB)
        connect_string = "tcp://" + self.router_ip_address + ':' + port_map.port_map[
            'publish_to_router_port']

        self.publisher.connect(connect_string)

        app.router.add_route('GET', '/poll', self.poll)
        await self.keep_alive()

        return srv

    async def setup_digital_pin(self, request):
        """
        This method handles the "set digital pin mode" block request
        :param request: HTTP request
        :return: HTTP response
        """
        command = "digital_pin_mode"
        board = request.match_info.get('board')
        enable = request.match_info.get('enable')
        enable = await self.check_cmd_enable_disable(enable)

        pin = request.match_info.get('pin')
        mode = request.match_info.get('mode')

        mode = await self.check_cmd_digital_mode(mode)
        command_msg = umsgpack.packb({u"command": command, u"enable": enable, u"pin": pin, u"mode": mode})

        await self.send_command_to_router(board, command_msg)

        return web.Response(body="ok".encode('utf-8'))

    async def setup_analog_pin(self, request):
        """
        This method handles the "set analog input pin mode"
        :param request: HTTP request
        :return: HTTP response
        """
        command = "analog_pin_mode"
        board = request.match_info.get('board')
        enable = request.match_info.get('enable')
        enable = await self.check_cmd_enable_disable(enable)

        pin = request.match_info.get('pin')
        command_msg = umsgpack.packb({u"command": command, u"enable": enable, u"pin": pin})
        # await self.send_command_to_router(board, command_msg)

        board = 'A' + board
        board = board.encode()
        self.publisher.send_multipart([board, command_msg])

        return web.Response(body="ok".encode('utf-8'))

    async def digital_write(self, request):
        """
        This method handles the digital write request
        :param request: HTTP request
        :return: HTTP response
        """
        command = "digital_write"
        board = request.match_info.get('board')
        pin = request.match_info.get('pin')
        value = request.match_info.get('value')
        command_msg = umsgpack.packb({u"command": command, u"pin": pin, u"value": value})
        await self.send_command_to_router(board, command_msg)

        return web.Response(body="ok".encode('utf-8'))

    async def analog_write(self, request):
        """
        This method handles the analog (PWM) write request
        :param request: HTTP request
        :return: HTTP response
        """
        command = "analog_write"
        board = request.match_info.get('board')
        pin = request.match_info.get('pin')
        value = request.match_info.get('value')
        command_msg = umsgpack.packb({u"command": command, u"pin": pin, u"value": value})
        await self.send_command_to_router(board, command_msg)

        return web.Response(body="ok".encode('utf-8'))

    async def play_tone(self, request):
        """
        This method handles the play tone request.
        :param request: HTTP request
        :return: HTTP response
        """
        command = 'play_tone'
        board = request.match_info.get('board')
        pin = request.match_info.get('pin')
        freq = request.match_info.get('frequency')
        duration = request.match_info.get('duration')
        command_msg = umsgpack.packb({u"command": command, u"pin": pin, u"frequency": freq, u"duration": duration})
        await self.send_command_to_router(board, command_msg)

        return web.Response(body="ok".encode('utf-8'))

    async def tone_off(self, request):
        """
        This method turns tone off.
        :param request: HTTP request
        :return: HTTP response
        """
        command = 'tone_off'
        board = request.match_info.get('board')
        pin = request.match_info.get('pin')

        command_msg = umsgpack.packb({u"command": command, u"pin": pin})
        await self.send_command_to_router(board, command_msg)

        return web.Response(body="ok".encode('utf-8'))

    async def set_servo_position(self, request):
        """
        This method sets a servo position.
        :param request: HTTP request
        :return: HTTP response
        """
        command = 'set_servo_position'
        board = request.match_info.get('board')
        pin = request.match_info.get('pin')
        position = request.match_info.get('position')

        command_msg = umsgpack.packb({u"command": command, u"pin": pin, u"position": position})
        await self.send_command_to_router(board, command_msg)

        return web.Response(body="ok".encode('utf-8'))

    # noinspection PyUnusedLocal
    async def poll(self, request):
        """
        This method handles the Scratch poll request for reporter data
        :param request: HTTP request
        :return: HTTP response
        """
        # save the reply to a temporary variable
        total_reply = self.poll_reply
        # if total_reply != '':
        #     print('r: ' + total_reply)

        # clear the poll reply string for the next reply set
        self.poll_reply = ""
        return web.Response(headers={"Access-Control-Allow-Origin": "*"},
                            content_type="text/html", charset="ISO-8859-1", text=total_reply)

    async def got_analog_report(self, request):
        """
        This method handles analog data reports being sent from s2aio servers
        :param request: HTTP request
        :return: HTTP response
        """
        board = request.match_info.get('board')
        pin = request.match_info.get('pin')
        value = request.match_info.get('value')
        self.poll_reply += 'analog_read/' + board + '/' + pin + ' ' + value + '\n'

        return web.Response(body="ok".encode('utf-8'))

    async def got_digital_report(self, request):
        """
        This method handles data data reports being sent from s2aio servers
        :param request: HTTP request
        :return: HTTP response
        """
        board = request.match_info.get('board')
        pin = request.match_info.get('pin')
        value = request.match_info.get('value')
        self.poll_reply += 'digital_read/' + board + '/' + pin + ' ' + value + '\n'

        return web.Response(body="ok".encode('utf-8'))

    async def got_problem_report(self, request):
        """
        This method handles problem (debugging) reports being sent from s2aio servers
        :param request: HTTP request
        :return: HTTP response
        """
        board = request.match_info.get('board')
        problem = request.match_info.get('problem')
        self.poll_reply += 'problem/' + board + ' ' + problem + '\n'
        return web.Response(body="ok".encode('utf-8'))

    async def send_command_to_router(self, board, message):
        """
        Create a topic message and send the multipart message to the router
        :param board:  board that message is destined for
        :param message: Command message from Scratch
        :return:
        """
        m_topic = 'A' + board
        topic = m_topic.encode()
        self.publisher.send_multipart([topic, message])

    async def keep_alive(self):
        """
        This method is used to keep the server up and running when not connected to Scratch
        :return:
        """
        while True:

            # check for reporter messages
            try:
                [address, contents] = self.subscriber.recv_multipart(zmq.NOBLOCK)
                payload = umsgpack.unpackb(contents)
                # print("[%s] %s" % (address, payload))
                board_num = address.decode()
                board_num = board_num[1]
                command = payload['command']
                # we will ignore any i2c_replies
                if command == 'i2c_reply' or command == 'i2c_request':
                    continue
                elif command == 'problem':
                    data_string = command + '/' + board_num + ' ' + payload['problem']
                else:
                    # noinspection PyPep8
                    if not 'pin' in payload:
                        continue
                    else:
                        pin = payload['pin']
                        value = payload['value']
                        data_string = command + '/' + board_num + '/' + pin + ' ' + value + '\n'
                    # print(data_string)
                self.poll_reply += data_string

            except zmq.error.Again:
                await asyncio.sleep(.001)

    async def check_cmd_enable_disable(self, command):
        """
        This method provides translation for enable/disable
        :param command: Language specific value for enable
        :return: English translation
        """
        if command in self.ln_ENABLE:
            return 'Enable'
        elif command in self.ln_DISABLE:
            return 'Disable'
        else:
            return 'invalid'

    # noinspection PyPep8Naming
    async def check_cmd_digital_mode(self, command):
        """
        This method provides translation for the digital mode.
        :param command: Mode in native language
        :return: Mode in english
        """
        if command in self.ln_INPUT:
            return 'Input'
        if command in self.ln_OUTPUT:
            return 'Output'
        if command in self.ln_PWM:
            return 'PWM'
        if command in self.ln_SERVO:
            return 'Servo'
        if command in self.ln_TONE:
            return 'Tone'
        if command in self.ln_SONAR:
            return 'SONAR'


def http_bridge():
    # noinspection PyShadowingNames

    parser = argparse.ArgumentParser()

    parser.add_argument('-r', dest='router_ip_address', default='None', help='Router IP Address')

    args = parser.parse_args()
    router_ip_address = args.router_ip_address

    # noinspection PyShadowingNames
    http_bridge = HttpBridge(router_ip_address)
    # noinspection PyShadowingNames
    loop = asyncio.get_event_loop()

    # noinspection PyBroadException
    try:
        loop.run_until_complete(http_bridge.init(loop))
    except KeyboardInterrupt:
        # noinspection PyShadowingNames
        loop = asyncio.get_event_loop()
        sys.exit(0)

    # signal handler function called when Control-C occurs
    # noinspection PyShadowingNames,PyUnusedLocal,PyUnusedLocal
    def signal_handler(signal, frame):
        print("Control-C detected. See you soon.")

        for t in asyncio.Task.all_tasks(loop):
            # noinspection PyBroadException
            try:
                t.cancel()
                loop.run_until_complete(asyncio.sleep(.1))
                loop.stop()
                loop.close()
            except:
                pass

        sys.exit(0)

    # listen for SIGINT
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


if __name__ == "__main__":

    try:
        http_bridge()
    except KeyboardInterrupt:
        sys.exit(0)

    loop = asyncio.get_event_loop()

    # noinspection PyBroadException
    try:
        loop.run_forever()
        loop.stop()
        loop.close()
    except:
        pass
