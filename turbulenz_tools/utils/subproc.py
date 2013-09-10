# Copyright (c) 2009-2011,2013 Turbulenz Limited

"""
Collection of utility functions for handling subprocess execution.
"""

import datetime
import subprocess

__version__ = '1.0.0'

class SubProc(object):
    """Encapsulation for running subprocesses, capturing the output and processing to return in a response."""
    def __init__(self, command, cwd=None):
        self.command = command
        self.cwd = cwd
        self.retcode = 0
        self.time_delta = datetime.timedelta()
        self.stdout_report, self.stderr_report = ('','')

    def update_command(self, command, cwd=None, env=None):
        """Set the command to execute and optionally the path to execute form."""
        self.command = command
        self.cwd = cwd

    def time_popen(self):
        """Time a subprocess command and return process retcode. This method will block until the process completes."""
        time_start = datetime.datetime.now()

        proc = subprocess.Popen(self.command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=self.cwd)
        stdout_report, stderr_report = proc.communicate()
        self.retcode = proc.wait()

        time_end = datetime.datetime.now()
        time_delta = time_end - time_start

        self.time_delta += time_delta
        self.stdout_report += stdout_report
        self.stderr_report += stderr_report

        return self.retcode

    def command_str(self):
        """Generate the command string."""
        return ' '.join(self.command)
