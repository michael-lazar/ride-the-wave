# -*- coding: utf-8 -*-
"""
TODO: Insert docstring here
"""

import time
import logging
from copy import copy
from miniboa import TelnetServer, telnet
# https://github.com/jquast/telnetlib3

IDLE_TIMEOUT = 30
CLIENT_LIST = []


# ANSI Color Codes
WATER = '\x1b[46m\x1b[1;37m'
BOLD = '\x1b[1m'
MAGENTA = '\x1b[1;35m'
YELLOW = '\x1b[1;33m'
GREEN = '\x1b[22;32m'
RED = '\x1b[1;31m'
END = '\x1b[0m'


WAVE = [
    "'^^'-.__.-" * 20,
    "^^'-.__.-'" * 20,
    "^'-.__.-'^" * 20,
    "'-.__.-'^^" * 20,
    "-.__.-'^^'" * 20,
    ".__.-'^^'-" * 20,
    "__.-'^^'-." * 20,
    "_.-'^^'-._" * 20,
    ".-'^^'-.__" * 20,
    "-'^^'-.__." * 20,
]


BANNER = [
    '                 ',
    '  M O Z Z . U S  ',
    '  -------------  ',
    '  Ride the Wave  ',
    '                 ',
]
BANNER_ROWS = len(BANNER)
BANNER_COLS = max(len(row) for row in BANNER)


def build_banner(offset=0):
    """
    Add custom ANSI styling to the banner text.

    Cycle through colors for the subtitle text, using a slower rate than the
    primary animation.
    """
    color = [MAGENTA, GREEN, RED, YELLOW][(offset // 7) % 4]

    banner = copy(BANNER)
    banner[0] = END + banner[0] + WATER
    banner[1] = END + BOLD + banner[1] + END + WATER
    banner[2] = END + banner[2] + WATER
    banner[3] = END + color + banner[3] + END + WATER
    banner[4] = END + banner[4] + WATER
    return banner


def build_frame(rows, cols, offset=0):
    """
    Construct the screen, given the dimensions of the terminal.
    """

    rows = max(rows, BANNER_ROWS)
    cols = max(cols, BANNER_COLS)
    lines = []

    # Add the background
    for i in range(rows):
        row_offset = (i + offset) % len(WAVE)
        lines.append(WAVE[row_offset][:cols])

    # Overlay the banner
    banner = build_banner(offset=offset)
    banner_start_row = (rows - BANNER_ROWS) // 2
    banner_start_col = (cols - BANNER_COLS) // 2
    for i, text in enumerate(banner, start=banner_start_row):
        start, end = banner_start_col, banner_start_col + BANNER_COLS
        lines[i] = lines[i][:start] + text + lines[i][end:]

    screen = '\n'.join(lines)
    screen = WATER + screen + END
    return screen


def on_connect(client):
    """
    Sample on_connect function.
    Handles new connections.
    """
    logging.info("Opened connection to {}".format(client.addrport()))

    client.request_naws()
    client.request_do_sga()
    client.request_will_echo()
    client.send('{}{}{}'.format(telnet.IAC, telnet.DO, telnet.LINEMO))

    client.offset = 0
    CLIENT_LIST.append(client)


def on_disconnect(client):
    """
    Sample on_disconnect function.
    Handles lost connections.
    """
    logging.info("Lost connection to {}".format(client.addrport()))
    CLIENT_LIST.remove(client)


def kick_idle():
    """
    Looks for idle clients and disconnects them by setting active to False.
    """
    for client in CLIENT_LIST:
        if client.idle() > IDLE_TIMEOUT:
            logging.info("Kicking idle lobby client from {}".format(
                client.addrport()))
            client.active = False


def draw():
    for client in CLIENT_LIST:
        client.send_cc('^s')
        client.offset += 1
        screen = build_frame(client.rows, client.columns, client.offset)
        client.send(screen)


if __name__ == '__main__':

    # Simple chat server to demonstrate connection handling via the
    # async and telnet modules.
    logging.basicConfig(level=logging.DEBUG)

    # Create a telnet server with a port, address,
    # a function to call with new connections
    # and one to call with lost connections.
    telnet_server = TelnetServer(
        port=7777,
        address='127.0.0.1',
        on_connect=on_connect,
        on_disconnect=on_disconnect,
        timeout=.05)

    logging.info("Listening for connections on port {}. "
                 "CTRL-C to break.".format(telnet_server.port))

    # Server Loop
    while True:
        telnet_server.poll()
        kick_idle()
        time.sleep(0.2)
        draw()
