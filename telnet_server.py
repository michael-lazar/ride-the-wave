# /usr/bin/env python
"""
An animated telnet splash screen for mozz.us.

When a connection is established with the server, an ASCII "wave" animation
is displayed on the screen. After a short period of the time, the connection
is automatically closed. The text rendering relies on some basic VT-100 ANSI
commands for text coloring and cursor movement.

The telnet server uses asyncio and requires python 3.5+.
"""

import logging
import asyncio
from telnetlib3 import telopt, create_server

__author__ = 'Michael Lazar'
__license__ = 'GNU GPL v3'
__copyright__ = '(c) 2019 Michael Lazar'
__version__ = '1.0.0'

PORT = '7777'
HOST = '127.0.0.1'

# VT-100 terminal commands
END = '\x1b[0m'
BOLD = '\x1b[1m'
RED = '\x1b[1;31m'
GREEN = '\x1b[22;32m'
YELLOW = '\x1b[1;33m'
MAGENTA = '\x1b[1;35m'
WATER = '\x1b[46m\x1b[1;37m'  # white w/ cyan background
MOVE = '\x1b[{};{}H'  # move cursor to (row, col) coordinates

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


def get_terminal_size(writer):
    """
    Grab the most recent terminal size reported by the client via telnet NAWS.


    """
    rows = writer.get_extra_info('rows', 24)
    cols = writer.get_extra_info('cols', 80)
    return rows, cols


async def negotiate_telnet_options(writer):
    """
    Negotiate the telnet connection options with the client.
    """
    # Ask the client to report their window size in rows x cols
    writer.iac(telopt.DO, telopt.NAWS)

    # Suppress go-ahead signals for efficiency
    writer.iac(telopt.DO, telopt.SGA)
    writer.iac(telopt.WONT, telopt.SGA)

    # Give the client a bit of time to respond to the commands before starting
    await asyncio.sleep(0.5)


def render_background(rows, cols, offset):
    """
    Fill the entire terminal with the wave pattern.

    Used on startup and when a terminal size change is detected.
    """
    lines = []
    for i in range(rows):
        row_offset = (offset - rows + i + 1) % len(WAVE)
        lines.append(render_wave(cols, row_offset))
    return '\r\n'.join(lines)


def render_wave(cols, offset):
    """
    Draw a single row of the wave animation.
    """
    return WATER + WAVE[offset][:cols] + END


def render_banner(rows, cols, offset):
    """
    Overlay the banner text on top of the wave animation.

    This is done utilizing the VT-100 move cursor command to avoid needing
    to redraw the entire screen.
    """
    if rows < len(BANNER) + 2 or cols < len(BANNER[0]) + 2:
        # The screen is too small to render the banner
        return ''

    color = [MAGENTA, GREEN, RED, YELLOW][(offset // 7) % 4]

    row = (rows - len(BANNER)) // 2
    col = (cols - len(BANNER[0])) // 2

    text = [

        MOVE.format(row, col) + BANNER[0],
        MOVE.format(row + 1, col) + BOLD + BANNER[1] + END,
        MOVE.format(row + 2, col) + BANNER[2],
        MOVE.format(row + 3, col) + color + BANNER[3] + END,
        MOVE.format(row + 4, col) + BANNER[4],
        MOVE.format(rows, 0),  # Reset cursor at the bottom of the screen
    ]
    return ''.join(text)


async def shell(reader, writer):

    await negotiate_telnet_options(writer)

    rows, cols = None, None
    for i in range(1):
        new_rows, new_cols = get_terminal_size(writer)

        # Draw the background
        offset = i % len(WAVE)
        if (new_rows, new_cols) == (rows, cols):
            writer.write('\r\n' + render_wave(cols, offset))
        else:
            rows, cols = new_rows, new_cols
            writer.write('\r\n' + render_background(rows, cols, offset))

        # Overlay the banner
        writer.write(render_banner(rows, cols, i))

        await writer.drain()
        await asyncio.sleep(0.1)

    writer.close()


def main():
    """
    Main server loop.
    """
    logging.basicConfig(level=logging.DEBUG)
    logging.info("Listening for connections on {}:{}.".format(HOST, PORT))

    loop = asyncio.get_event_loop()
    coro = create_server(host=HOST, port=PORT, shell=shell)
    server = loop.run_until_complete(coro)
    loop.run_until_complete(server.wait_closed())


if __name__ == '__main__':
    main()
