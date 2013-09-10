# Copyright (c) 2009-2011,2013 Turbulenz Limited
"""Utility module to colour highlight the output form tools."""

import sys
import re

# pylint: disable=R0903
class ColouredWriterBase(object):
    """Colour th Django server output."""
    colors = {  'endc': '\033[0m',              # black
                'fail': '\033[91m',             # red
                'okgreen': '\033[32m',          # green
                'unknown': '\033[33m',          # yellow
                'okblue': '\033[34m',           # blue
                'warning': '\033[95m',          # magenta
                'build': '\033[97m\033[40m' }   # white

    status_code_text = {
            100: 'CONTINUE',
            101: 'SWITCHING PROTOCOLS',
            200: 'OK',
            201: 'CREATED',
            202: 'ACCEPTED',
            203: 'NON-AUTHORITATIVE INFORMATION',
            204: 'NO CONTENT',
            205: 'RESET CONTENT',
            206: 'PARTIAL CONTENT',
            300: 'MULTIPLE CHOICES',
            301: 'MOVED PERMANENTLY',
            302: 'FOUND',
            303: 'SEE OTHER',
            304: 'NOT MODIFIED',
            305: 'USE PROXY',
            306: 'RESERVED',
            307: 'TEMPORARY REDIRECT',
            400: 'BAD REQUEST',
            401: 'UNAUTHORIZED',
            402: 'PAYMENT REQUIRED',
            403: 'FORBIDDEN',
            404: 'NOT FOUND',
            405: 'METHOD NOT ALLOWED',
            406: 'NOT ACCEPTABLE',
            407: 'PROXY AUTHENTICATION REQUIRED',
            408: 'REQUEST TIMEOUT',
            409: 'CONFLICT',
            410: 'GONE',
            411: 'LENGTH REQUIRED',
            412: 'PRECONDITION FAILED',
            413: 'REQUEST ENTITY TOO LARGE',
            414: 'REQUEST-URI TOO LONG',
            415: 'UNSUPPORTED MEDIA TYPE',
            416: 'REQUESTED RANGE NOT SATISFIABLE',
            417: 'EXPECTATION FAILED',
            500: 'INTERNAL SERVER ERROR',
            501: 'NOT IMPLEMENTED',
            502: 'BAD GATEWAY',
            503: 'SERVICE UNAVAILABLE',
            504: 'GATEWAY TIMEOUT',
            505: 'HTTP VERSION NOT SUPPORTED',
        }

    def __init__(self, stdout, stderr):
        self.stdout = stdout
        self.stderr = stderr

    def flush(self):
        """Flush method."""
        self.stdout.flush()
        self.stderr.flush()

if sys.platform == "win32":

    from ctypes import windll, Structure, c_short, c_ushort, byref

    SHORT = c_short
    WORD = c_ushort

    class Coord(Structure):
        """struct in wincon.h."""
        _fields_ = [
            ("X", SHORT),
            ("Y", SHORT)]

    class SmallRect(Structure):
        """struct in wincon.h."""
        _fields_ = [
            ("Left", SHORT),
            ("Top", SHORT),
            ("Right", SHORT),
            ("Bottom", SHORT)]

    class ConsoleScreenBufferInfo(Structure):
        """struct in wincon.h."""
        _fields_ = [
            ("dwSize", Coord),
            ("dwCursorPosition", Coord),
            ("wAttributes", WORD),
            ("srWindow", SmallRect),
            ("dwMaximumWindowSize", Coord)]

    # winbase.h
    STD_INPUT_HANDLE = -10
    STD_OUTPUT_HANDLE = -11
    STD_ERROR_HANDLE = -12

    # wincon.h
    FOREGROUND_BLACK     = 0x0000
    FOREGROUND_BLUE      = 0x0001
    FOREGROUND_GREEN     = 0x0002
    FOREGROUND_CYAN      = 0x0003
    FOREGROUND_RED       = 0x0004
    FOREGROUND_MAGENTA   = 0x0005
    FOREGROUND_YELLOW    = 0x0006
    FOREGROUND_GREY      = 0x0007
    FOREGROUND_INTENSITY = 0x0008 # foreground color is intensified.

    BACKGROUND_BLACK     = 0x0000
    BACKGROUND_BLUE      = 0x0010
    BACKGROUND_GREEN     = 0x0020
    BACKGROUND_CYAN      = 0x0030
    BACKGROUND_RED       = 0x0040
    BACKGROUND_MAGENTA   = 0x0050
    BACKGROUND_YELLOW    = 0x0060
    BACKGROUND_GREY      = 0x0070
    BACKGROUND_INTENSITY = 0x0080 # background color is intensified.

    STDOUT_HANDLE = windll.kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
    SETCONSOLETEXTATTRIBUTE = windll.kernel32.SetConsoleTextAttribute
    GETCONSOLESCREENBUFFERINFO = windll.kernel32.GetConsoleScreenBufferInfo

    def get_text_attr():
        """Returns the character attributes (colors) of the console screen buffer."""
        csbi = ConsoleScreenBufferInfo()
        GETCONSOLESCREENBUFFERINFO(STDOUT_HANDLE, byref(csbi))
        return csbi.wAttributes

    def set_text_attr(color):
        """Sets the character attributes (colors) of the console screen buffer. Color is a combination of foreground
        and background color, foreground and background intensity."""
        SETCONSOLETEXTATTRIBUTE(STDOUT_HANDLE, color)

    class ColouredWriter(ColouredWriterBase):
        """Colour the Django server output."""
        colors = {  'endc': FOREGROUND_BLACK | FOREGROUND_INTENSITY,        # white
                    'fail': FOREGROUND_RED,                                 # red
                    'okgreen': FOREGROUND_GREEN,                            # green
                    'unknown': FOREGROUND_YELLOW,                           # yellow
                    'okblue': FOREGROUND_BLUE | FOREGROUND_INTENSITY,       # blue
                    'warning':FOREGROUND_MAGENTA | FOREGROUND_INTENSITY,    # magenta
                    'build': BACKGROUND_BLACK | BACKGROUND_INTENSITY | FOREGROUND_BLACK } # white

        #[14/Jul/2009 18:57:31] "GET /assets/maps/mp/q4ctf1.proc HTTP/1.1" 302 0
        line_re = re.compile('^(\[.*\]) (".*") (\d*) (\d*)$')
        build_re = re.compile("^(\[.*\]) ('.*')$")

        def __init__(self, stdout, stderr):
            ColouredWriterBase.__init__(self, stdout, stderr)
            self.default_colors = get_text_attr()
            self.default_bg = self.default_colors & 0x0070

        def write(self, line):
            """Write method."""
            line_m = ColouredWriter.line_re.match(line)
            if line_m:
                time = line_m.group(1)
                request = line_m.group(2)
                code = int(line_m.group(3))
                size = int(line_m.group(4))
                if code >= 500:
                    command = ColouredWriter.colors['fail']
                elif code >= 400:
                    command = ColouredWriter.colors['warning']
                elif code == 301:
                    command = ColouredWriter.colors['fail'] # We don't want any 301s from our links...
                elif code >= 300:
                    command = ColouredWriter.colors['okgreen']
                elif code >= 200:
                    command = ColouredWriter.colors['okblue']
                else:
                    command = ColouredWriter.colors['unknown']

                if code in ColouredWriter.status_code_text:
                    meaning = ColouredWriter.status_code_text[code]
                else:
                    meaning = "*unknown*"

                self.stdout.write(time)
                set_text_attr(command | self.default_bg)
                self.stdout.write(" " + request)
                set_text_attr(self.default_colors)
                self.stdout.write(" %i %i (%s)\n" % (code, size, meaning))
            else:
                build_m = ColouredWriter.build_re.match(line)
                if build_m:
                    time = build_m.group(1)
                    request = build_m.group(2)
                    self.stdout.write(time + ' ')
                    if request[1:].startswith("FAILED"):
                        set_text_attr(ColouredWriter.colors['fail'])
                    else:
                        set_text_attr(ColouredWriter.colors['build'] | self.default_bg)
                    self.stdout.write("%s" % (request))
                    set_text_attr(self.default_colors)
                    self.stdout.write("\n")
                else:
                    self.stdout.write(line)

else:

    class ColouredWriter(ColouredWriterBase):
        """Colour the Django server output."""
        colors = {  'endc': '\033[0m',               # black
                    'fail': '\033[91m',              # red
                    'okgreen': '\033[32m',           # green
                    'unknown': '\033[33m',           # yellow
                    'okblue': '\033[34m',            # blue
                    'warning': '\033[95m',           # magenta
                    'buildfail': '\033[91m\033[40m', # red on black
                    'buildmsg': '\033[32m\033[40m',  # green on black
                    'build': '\033[97m\033[40m' }    # white on black

        #[14/Jul/2009 18:57:31] "GET /assets/maps/mp/q4ctf1.proc HTTP/1.1" 302 0
        line_re = re.compile('^(\[.*\]) (".*") (\d*) (\d*)$')
        build_re = re.compile("^(\[.*\]) ('.*')$")

        # 127.0.0.1 0.0.0.0:8000 - [06/Sep/2009:21:40:00 +0100]
        #    "GET /assets/models/mapobjects/multiplayer/acceleration_pad/acceleration_pad_d.dds HTTP/1.1" 200 87125
        #    "http://0.0.0.0:8000/play/maps/mp/q4ctf1.map"
        #    "Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6; en-us) AppleWebKit/532.0+ (KHTML, like Gecko) \
        #        Version/4.0.3 Safari/531.9"
        access_re = re.compile('^([\d\.]*) ([\w\.:-]*) - (\[.*\]) (".*") (\d*) (\d*) (".*") (".*")$')

        @classmethod
        def coloured_access(cls, time, request, code, size, server, who=None):
            """Generate a consistent coloured response."""
            if code >= 500:
                command = ColouredWriter.colors['fail']
            elif code >= 400:
                command = ColouredWriter.colors['warning']
            elif code == 301:
                command = ColouredWriter.colors['fail'] # We don't want any 301s from our links...
            elif code >= 300:
                command = ColouredWriter.colors['okgreen']
            elif code >= 200:
                command = ColouredWriter.colors['okblue']
            else:
                command = ColouredWriter.colors['unknown']

            if code in ColouredWriter.status_code_text:
                meaning = ColouredWriter.status_code_text[code]
            else:
                meaning = "*unknown*"

            endc = ColouredWriter.colors['endc']
            if who is None:
                line = "%s %s %s%s%s %i %i (%s)\n" % (server[:3], time, command, request, endc, code, size, meaning)
            else:
                line = "%s %s %s %s%s%s %i %i (%s)\n" % \
                    (server[:3], time, who, command, request, endc, code, size, meaning)
            return line

        def write(self, line):
            """Write method."""
            access_m = ColouredWriter.access_re.match(line)
            line_m = ColouredWriter.line_re.match(line)
            build_m = ColouredWriter.build_re.match(line)
            if access_m:
                server = "LIGHTTPD"
                time = access_m.group(3)
                who = access_m.group(1)
                request = access_m.group(4)
                code = int(access_m.group(5))
                size = int(access_m.group(6))
                line = ColouredWriter.coloured_access(time, request, code, size, server, who)
            elif line_m:
                server = "PYTHON"
                time = line_m.group(1)
                request = line_m.group(2)
                code = int(line_m.group(3))
                size = int(line_m.group(4))
                line = ColouredWriter.coloured_access(time, request, code, size, server)
            elif build_m:
                server = "BUILD"
                time = build_m.group(1)
                request = build_m.group(2)
                if request[1:].startswith("FAILED"):
                    build = ColouredWriter.colors['buildfail']
                elif request[1:].startswith("MSG"):
                    build = ColouredWriter.colors['buildmsg']
                else:
                    build = ColouredWriter.colors['build']
                endc = ColouredWriter.colors['endc']
                line = "%s %s %s%s%s\n" % (server[:3], time, build, request, endc)

            self.stdout.write(line)
            self.stdout.flush()

if __name__ == "__main__":
    CONVERTER = ColouredWriter(sys.stdout, sys.stderr)
    while True:
        L = sys.stdin.readline()
        CONVERTER.write(L)
