# /usr/bin/env python
"""
An animated telnet splash screen for mozz.us.

When a connection is established with the server, an ASCII "wave" animation
is displayed on the screen. After a short period of the time, the connection
is automatically closed. The text rendering relies on some universal VT-100
ANSI commands for text coloring.

The telnet server uses asyncio and requires python 3.6+.

ASCII art credited to Joan Stark:
https://web.archive.org/web/20091028022938/http://www.geocities.com/SoHo/7373/scroll.htm
"""

__author__ = 'Michael Lazar'
__license__ = 'GNU GPL v3'
__copyright__ = '(c) 2019 Michael Lazar'
__version__ = '1.0.0'

import logging
import asyncio
import argparse
from functools import lru_cache
from telnetlib3 import telopt, create_server

# VT-100 terminal commands
END = '\x1b[0m'
CLEAR = '\x1b[2J'
BOLD = '\x1b[1m'
RED = '\x1b[1;31m'
GREEN = '\x1b[22;32m'
YELLOW = '\x1b[1;33m'
MAGENTA = '\x1b[1;35m'
HIDE_CURSOR = '\x1b[25l'
WATER = '\x1b[46m\x1b[1;37m'  # white w/ cyan background
RESET = '\x1b[0;0H'  # move cursor to (0, 0) coordinates

FPS = 10
DURATION = 10

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
    BOLD + '  M O Z Z . U S  ' + END,
    '  -------------  ',
    '^color' + '  Ride the Wave  ' + END,
    '                 ',
]
BANNER_ROWS = len(BANNER)
BANNER_COLS = len(BANNER[0])


def parse_args():
    """
    Parse command line arguments.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', default=7777, type=int)
    parser.add_argument('--fps', default=FPS, type=float)
    parser.add_argument('--duration', default=DURATION, type=float)
    return parser.parse_args()


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
    writer.iac(telopt.DO, telopt.NAWS)
    writer.iac(telopt.DO, telopt.SGA)
    writer.iac(telopt.WILL, telopt.SGA)
    writer.iac(telopt.WILL, telopt.ECHO)
    writer.iac(telopt.WONT, telopt.LINEMODE)

    # Give the client a bit of time to respond to the commands before starting.
    # This prevents needing to resize the animation 1-2 frames when the NAWS
    # response finally comes back.
    await asyncio.sleep(0.5)


@lru_cache(maxsize=200)
def render_screen(rows, cols, offset):
    """
    Render a frame of the animation screen.

    This method is cached because if the client doesn't resize their window,
    the animation will be repeated every len(WAVE) frames.
    """
    # Fill in the background with the wave pattern
    lines = [WAVE[(i + offset) % len(WAVE)][:cols] for i in range(rows)]

    # Overlay the banner on top of the background
    overlay_banner(rows, cols, lines)

    # Add the footer - author's sig and instructions
    if len(lines[-1]) > 9:
        lines[-1] = 'jgs' + lines[-1][3:-6] + '[q]uit'

    return RESET + WATER + '\r\n'.join(lines) + END


def overlay_banner(rows, cols, lines):
    """
    Overlay the banner text on top of the background pattern.
    """
    if rows < BANNER_ROWS or cols < BANNER_COLS:
        return lines

    start_row = (rows - BANNER_ROWS) // 2
    start = (cols - BANNER_COLS) // 2
    end = start + BANNER_COLS
    for i, line in enumerate(BANNER):
        row = start_row + i
        lines[row] = lines[row][:start] + END + line + WATER + lines[row][end:]


async def shell(reader, writer):
    """
    A coroutine that's invoked after a new connection has been established.
    """
    await negotiate_telnet_options(writer)

    for frame in range(int(DURATION * FPS)):
        rows, cols = get_terminal_size(writer)

        offset = frame % len(WAVE)
        text = render_screen(rows, cols, offset)

        # The color cycles once every 7 frames. Add this after render_screen()
        # so we can cache everything else on the screen.
        subtitle_color = [MAGENTA, GREEN, RED, YELLOW][(frame // 7) % 4]
        text = text.replace('^color', subtitle_color, 1)

        writer.write(text)
        await writer.drain()

        try:
            char = await asyncio.wait_for(reader.read(1), timeout=1/FPS)
            if char == 'q':
                break
        except asyncio.TimeoutError:
            pass

    writer.close()


def main():
    """
    Main entry point.
    """
    args = parse_args()

    logging.basicConfig(level=logging.INFO)
    logging.info(f'Listening on {args.host}:{args.port}.')

    global FPS
    FPS = args.fps
    logging.info(f'Animation speed {FPS} fps')

    global DURATION
    DURATION = args.duration
    logging.info(f'Duration {DURATION} seconds')

    loop = asyncio.get_event_loop()
    coro = create_server(host=args.host, port=args.port, shell=shell)
    server = loop.run_until_complete(coro)
    loop.run_until_complete(server.wait_closed())


if __name__ == '__main__':
    main()
