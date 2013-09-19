#!/usr/bin/env python
# Copyright (c) 2012-2013 Turbulenz Limited

from logging import basicConfig, CRITICAL, INFO, WARNING

import argparse
from urllib3 import connection_from_url
from urllib3.exceptions import HTTPError, SSLError
from simplejson import loads as json_loads, dump as json_dump
from gzip import GzipFile
from zlib import decompress as zlib_decompress
from time import strptime, strftime, gmtime
from calendar import timegm
from re import compile as re_compile
from sys import stdin, argv
from os import mkdir
from os.path import exists as path_exists, join as path_join, normpath
from getpass import getpass, GetPassWarning
from base64 import urlsafe_b64decode

__version__ = '2.1.2'
__dependencies__ = []


HUB_COOKIE_NAME = 'hub'
HUB_URL = 'https://hub.turbulenz.com/'

DATATYPE_DEFAULT = 'events'
DATATYPE_URL = { 'events': '/dynamic/project/%s/event-log',
                 'users': '/dynamic/project/%s/user-info' }

DAY = 86400
TODAY_START = (timegm(gmtime()) / DAY) * DAY

# pylint: disable=C0301
USERNAME_PATTERN = re_compile('^[a-z0-9]+[a-z0-9-]*$') # usernames
PROJECT_SLUG_PATTERN = re_compile('^[a-zA-Z0-9\-]*$') # game
# pylint: enable=C0301

class DateRange(object):
    """Maintain a time range between two dates. If only a start time is given it will generate a 24 hour period
       starting at that time. Defaults to the start of the current day if no times are given"""
    def __init__(self, start=TODAY_START, end=None):
        self.start = start
        if end:
            self.end = end
        else:
            self.end = start + DAY
        if self.start > self.end:
            raise ValueError('Start date can\'t be greater than the end date')

        def _range_str(t):
            if t % DAY:
                return strftime('%Y-%m-%d %H:%M:%SZ', gmtime(t))
            else:
                return strftime('%Y-%m-%d', gmtime(t))
        self.start_str = _range_str(self.start)
        if self.end % DAY:
            self.end_str = _range_str(self.end)
        else:
            self.end_str = _range_str(self.end - DAY)


    def filename_str(self):
        if self.start_str == self.end_str:
            return self.start_str
        elif int(self.start / DAY) == int(self.end / DAY):
            result = '%s_-_%s' % (strftime('%Y-%m-%d %H:%M:%SZ', gmtime(self.start)),
                                  strftime('%Y-%m-%d %H:%M:%SZ', gmtime(self.end)))
            return result.replace(' ', '_').replace(':', '-')
        else:
            result = '%s_-_%s' % (self.start_str, self.end_str)
            return result.replace(' ', '_').replace(':', '-')

    @staticmethod
    def parse(range_str):
        date_format = '%Y-%m-%d'
        range_parts = range_str.split(':')

        if len(range_parts) < 1:
            error('Date not set')
            exit(1)
        elif len(range_parts) > 2:
            error('Can\'t provide more than two dates for date range')
            exit(1)

        try:
            start = int(timegm(strptime(range_parts[0], date_format)))
            end = None
            if len(range_parts) == 2:
                end = int(timegm(strptime(range_parts[1], date_format))) + DAY
        except ValueError:
            error('Dates must be in the yyyy-mm-dd format')
            exit(1)

        return DateRange(start, end)


def log(message, new_line=True):
    print '\r >> %s' % message,
    if new_line:
        print

def error(message):
    log('[ERROR]   - %s' % message)

def warning(message):
    log('[WARNING] - %s' % message)


def _parse_args():
    parser = argparse.ArgumentParser(description="Export event logs and anonymised user information of a game.")
    parser.add_argument("-v", "--verbose", action="store_true", help="verbose output")
    parser.add_argument("-s", "--silent", action="store_true", help="silent running")
    parser.add_argument("--version", action='version', version=__version__)

    parser.add_argument("-u", "--user", action="store",
                        help="Hub login username (will be requested if not provided)")
    parser.add_argument("-p", "--password", action="store",
                        help="Hub login password (will be requested if not provided)")

    parser.add_argument("-t", "--type", action="store", default=DATATYPE_DEFAULT,
                        help="type of data to download, either events or users (defaults to " + DATATYPE_DEFAULT + ")")
    parser.add_argument("-d", "--daterange", action="store", default=TODAY_START,
                        help="individual 'yyyy-mm-dd' or range 'yyyy-mm-dd : yyyy-mm-dd' of dates to get the data " \
                             "for (defaults to today)")
    parser.add_argument("-o", "--outputdir", action="store", default="",
                        help="folder to output the downloaded files to (defaults to current directory)")

    parser.add_argument("-w", "--overwrite", action="store_true",
                        help="if a file to be downloaded exists in the output directory, " \
                             "overwrite instead of skipping it")
    parser.add_argument("--indent", action="store_true", help="apply indentation to the JSON output")
    parser.add_argument("--hub", default=HUB_URL, help="Hub url (defaults to https://hub.turbulenz.com/)")

    parser.add_argument("project", metavar='project_slug', help="Slug of Hub project you wish to download from")

    args = parser.parse_args(argv[1:])

    if args.silent:
        basicConfig(level=CRITICAL)
    elif args.verbose:
        basicConfig(level=INFO)
    else:
        basicConfig(level=WARNING)

    if not PROJECT_SLUG_PATTERN.match(args.project):
        error('Incorrect "project" format')
        exit(-1)

    username = args.user
    if not username:
        print 'Username: ',
        username = stdin.readline()
        if not username:
            error('Login information required')
            exit(-1)
        username = username.strip()
        args.user = username

    if not USERNAME_PATTERN.match(username):
        error('Incorrect "username" format')
        exit(-1)

    if not args.password:
        try:
            args.password = getpass()
        except GetPassWarning:
            error('Echo free password entry unsupported. Please provide a --password argument')
            return -1

    if args.type not in ['events', 'users']:
        error('Type must be one of \'events\' or \'users\'')
        exit(1)

    if isinstance(args.daterange, int):
        args.daterange = DateRange(args.daterange)
    else:
        args.daterange = DateRange.parse(args.daterange)

    return args


def login(connection, options):
    username = options.user
    password = options.password

    if not options.silent:
        log('Login as "%s".' % username)

    credentials = {'login': username,
                   'password': password,
                   'source': '/tool'}

    try:
        r = connection.request('POST',
                               '/dynamic/login',
                               fields=credentials,
                               retries=1,
                               redirect=False)
    except (HTTPError, SSLError):
        error('Connection to Hub failed!')
        exit(-1)

    if r.status != 200:
        if r.status == 301:
            redirect_location = r.headers.get('location', '')
            end_domain = redirect_location.find('/dynamic/login')
            error('Login is being redirected to "%s". Please verify the Hub URL.' % redirect_location[:end_domain])
        else:
            error('Wrong user login information!')
        exit(-1)

    cookie = r.headers.get('set-cookie', None)
    login_info = json_loads(r.data)

    # pylint: disable=E1103
    if not cookie or HUB_COOKIE_NAME not in cookie or login_info.get('source') != credentials['source']:
        error('Hub login failed!')
        exit(-1)
    # pylint: enable=E1103

    return cookie


def logout(connection, cookie):
    try:
        connection.request('POST',
                           '/dynamic/logout',
                           headers={'Cookie': cookie},
                           redirect=False)
    except (HTTPError, SSLError) as e:
        error(str(e))


def _request_data(options):
    daterange = options.daterange
    params = { 'start_time': daterange.start,
               'end_time': daterange.end,
               'version': __version__ }

    connection = connection_from_url(options.hub, timeout=8.0)
    cookie = login(connection, options)

    try:
        r = connection.request('GET',
                               DATATYPE_URL[options.type] % options.project,
                               headers={'Cookie': cookie,
                                        'Accept-Encoding': 'gzip'},
                               fields=params,
                               redirect=False)
    except (HTTPError, SSLError) as e:
        error(e)
        exit(-1)

    # pylint: disable=E1103
    r_data = json_loads(r.data)
    if r.status != 200:
        error_msg = 'Wrong Hub answer.'
        if r_data.get('msg', None):
            error_msg += ' ' + r_data['msg']
        if r.status == 403:
            error_msg += ' Make sure the project you\'ve specified exists and you have access to it.'
        error(error_msg)
        exit(-1)
    # pylint: enable=E1103

    if options.verbose:
        log('Data received from the hub')
        log('Logging out')
    logout(connection, cookie)

    return r_data


def write_to_file(options, data, filename=None, output_path=None, force_overwrite=False):
    if not filename:
        filename = '%s-%s-%s.json' % (options.project, options.type, options.daterange.filename_str())

    try:
        if not output_path:
            output_path = normpath(path_join(options.outputdir, filename))

        if path_exists(output_path):
            if options.overwrite or force_overwrite:
                if not options.silent:
                    warning('Overwriting existing file: %s' % output_path)
            elif not options.silent:
                warning('Skipping existing file: %s' % output_path)
                return

        indentation = None
        if options.indent:
            indentation = 4
            if isinstance(data, str):
                data = json_loads(data)

        with open(output_path, 'wb') as fout:
            if isinstance(data, str):
                fout.write(data)
            else:
                json_dump(data, fout, indent=indentation)

        if options.verbose:
            log('Finished writing to: %s' % output_path)

    except (IOError, OSError) as e:
        error(e)
        exit(-1)


try:
    # pylint: disable=F0401
    from Crypto.Cipher.AES import new as aes_new, MODE_CBC
    # pylint: enable=F0401

    def decrypt_data(data, key):
        # Need to use a key of length 32 bytes for AES-256
        if len(key) != 32:
            error('Invalid key length for AES-256')
            exit(-1)

        # IV is last 16 bytes
        iv = data[-16 :]
        data = data[: -16]

        data = aes_new(key, MODE_CBC, iv).decrypt(data)

        # Strip PKCS7 padding required for CBC
        if len(data) % 16:
            error('Corrupted data - invalid length')
            exit(-1)
        num_padding = ord(data[-1])
        if num_padding > 16:
            error('Corrupted data - invalid padding')
            exit(-1)

        return data[: -num_padding]

except ImportError:
    from io import BytesIO
    from subprocess import Popen, STDOUT, PIPE
    from struct import pack

    def decrypt_data(data, key):
        # Need to use a key of length 32 bytes for AES-256
        if len(key) != 32:
            error('Invalid key length for AES-256')
            exit(-1)

        aesdata = BytesIO()
        aesdata.write(key)
        aesdata.write(pack('I', len(data)))
        aesdata.write(data)
        process = Popen('aesdecrypt', stderr=STDOUT, stdout=PIPE, stdin=PIPE, shell=True)
        output, _ = process.communicate(input=aesdata.getvalue())
        retcode = process.poll()
        if retcode != 0:
            error('Failed to run aesdecrypt, check it is on the path or install PyCrypto')
            exit(-1)
        return str(output)


def get_log_files_local(options, files_list, enc_key):

    verbose = options.verbose
    silent = options.silent
    overwrite = options.overwrite
    output_dir = options.outputdir
    filename_prefix = options.project + '-'

    try:
        for filename in files_list:
            if filename.startswith('http'):
                error('Unexpected file to retrieve')
                exit(-1)
            # Format v1: 'eventlogspath/gamefolder/events-yyyy-mm-dd.json.gz'
            # Format v2: 'eventlogspath/gamefolder/events-yyyy-mm-dd.bin'
            # Convert to 'gameslug-events-yyyy-mm-dd.json'
            filename_patched = filename_prefix + filename.rsplit('/', 1)[-1].split('.', 1)[0] + '.json'

            output_path = normpath(path_join(output_dir, filename_patched))
            if not overwrite and path_exists(output_path):
                if not silent:
                    warning('Skipping existing file: %s' % output_path)
                continue

            if verbose:
                log('Retrieving file: %s' % filename_patched)

            if filename.endswith('.bin'):
                with open(filename, 'rb') as fin:
                    file_content = fin.read()
                file_content = decrypt_data(file_content, enc_key)
                file_content = zlib_decompress(file_content)

            else:   # if filename.endswith('.json.gz'):
                gzip_file = GzipFile(filename=filename, mode='rb')
                file_content = gzip_file.read()
                gzip_file.close()
                file_content = decrypt_data(file_content, enc_key)

            write_to_file(options, file_content, filename=filename_patched, output_path=output_path)

    except (IOError, OSError) as e:
        error(e)
        exit(-1)


def get_log_files_s3(options, files_list, enc_key, connection):

    verbose = options.verbose
    silent = options.silent
    overwrite = options.overwrite
    output_dir = options.outputdir
    filename_prefix = options.project + '-'

    try:
        for filename in files_list:
            # Format v1: 'https://bucket.s3.amazonaws.com/gamefolder/events-yyyy-mm-dd.json?AWSAccessKeyId=keyid
            #             &Expires=timestamp&Signature=signature'
            # Format v2: 'https://bucket.s3.amazonaws.com/gamefolder/events-yyyy-mm-dd.bin?AWSAccessKeyId=keyid
            #             &Expires=timestamp&Signature=signature'
            # Convert to 'gameslug-events-yyyy-mm-dd.json'
            filename_cleaned = filename.split('?', 1)[0].rsplit('/', 1)[-1]
            filename_patched = filename_prefix + filename_cleaned.split('.', 1)[0] + '.json'

            output_path = normpath(path_join(output_dir, filename_patched))
            if not overwrite and path_exists(output_path):
                if not silent:
                    warning('Skipping existing file: %s' % output_path)
                continue

            if verbose:
                log('Requesting file: %s' % filename_patched)
            r = connection.request('GET', filename, redirect=False)

            # pylint: disable=E1103
            if r.status != 200:
                error_msg = 'Couldn\'t download %s.' % filename_patched
                if r.data.get('msg', None):
                    error_msg += ' ' + r.data['msg']
                error(str(r.status) + error_msg)
                exit(-1)
            # pylint: enable=E1103

            r_data = decrypt_data(r.data, enc_key)

            if filename_cleaned.endswith('.bin'):
                r_data = zlib_decompress(r_data)
            # Format v1 file gets uncompressed on download so we just decrypt it

            write_to_file(options, r_data, filename=filename_patched, output_path=output_path)

    except (HTTPError, SSLError) as e:
        error(e)
        exit(-1)


def get_objectid_timestamp(objectid):
    return int(str(objectid)[0:8], 16)


def inline_array_events_local(options, today_log, array_files_list, enc_key):

    verbose = options.verbose
    to_sort = set()

    try:
        index = 0
        for index, filename in enumerate(array_files_list):
            # Format: 'eventlogspath/gamefolder/arrayevents/date(seconds)/objectid.bin'
            # The objectid doesn't correspond to a database entry but is used for uniqueness and timestamp
            filename = filename.replace('\\', '/')
            event_objectid = filename.rsplit('/', 1)[-1].split('.', 1)[0]
            timestamp = get_objectid_timestamp(event_objectid)
            formatted_timestamp = strftime('%Y-%m-%d %H:%M:%S', gmtime(timestamp))

            if verbose:
                log('Retrieving events file ' + str(index + 1) + ' submitted at ' + formatted_timestamp)

            with open(filename, 'rb') as fin:
                file_content = fin.read()
            file_content = decrypt_data(file_content, enc_key)
            file_content = json_loads(zlib_decompress(file_content))

            if not isinstance(file_content, list):
                file_content = [file_content]
            for event in file_content:
                slug = event['slug']
                del event['slug']
                event['time'] = strftime('%Y-%m-%d %H:%M:%S', gmtime(event['time']))

                if slug not in today_log:
                    today_log[slug] = { 'playEvents': [], 'customEvents': [] }

                today_log[slug]['customEvents'].append(event)
                # Maintaining a list of slugs to sort the customEvents by date for so that added array events appear in
                # order but we do not unneccesarily sort large lists if an array event wasn't added to it
                to_sort.add(slug)

        for slug in to_sort:
            today_log[slug]['customEvents'].sort(key=lambda k: k['time'])

        return today_log

    except (IOError, OSError) as e:
        error(e)
        exit(-1)


def inline_array_events_s3(options, today_log, array_files_list, enc_key, connection):

    verbose = options.verbose
    to_sort = set()

    try:
        for index, filename in enumerate(array_files_list):
            # Format: 'https://bucket.s3.amazonaws.com/gamefolder/arrayevents/date(seconds)/objectid.bin?
            #          AWSAccessKeyId=keyid&Expires=timestamp&Signature=signature'
            # The objectid doesn't correspond to a database entry but it used for uniqueness and timestamp
            filename_cleaned = filename.split('?', 1)[0].rsplit('/', 1)[-1]
            event_objectid = filename_cleaned.split('.', 1)[0]
            timestamp = get_objectid_timestamp(event_objectid)
            formatted_timestamp = strftime('%Y-%m-%d %H:%M:%S', gmtime(timestamp))

            if verbose:
                log('Requesting events file ' + str(index + 1) + ' submitted at ' + formatted_timestamp)
            r = connection.request('GET', filename, redirect=False)

            # pylint: disable=E1103
            if r.status != 200:
                error_msg = 'Couldn\'t download event %d.' % (index + 1)
                if r.data.get('msg', None):
                    error_msg += ' ' + r.data['msg']
                error(str(r.status) + error_msg)
                exit(-1)
            # pylint: enable=E1103

            r_data = decrypt_data(r.data, enc_key)
            r_data = json_loads(zlib_decompress(r_data))

            if not isinstance(r_data, list):
                r_data = [r_data]

            for event in r_data:
                slug = event['slug']
                del event['slug']
                event['time'] = strftime('%Y-%m-%d %H:%M:%S', gmtime(event['time']))

                if slug not in today_log:
                    today_log[slug] = { 'playEvents': [], 'customEvents': [] }

                today_log[slug]['customEvents'].append(event)
                # Maintaining a list of slugs to sort the customEvents by date for so that added array events appear in
                # order but we do not unneccesarily sort large lists if an array event wasn't added to it
                to_sort.add(slug)

        for slug in to_sort:
            today_log[slug]['customEvents'].sort(key=lambda k: k['time'])

        return today_log

    except (HTTPError, SSLError) as e:
        error(e)
        exit(-1)


def patch_and_write_today_log(options, resp_daterange, today_log, array_files_list, enc_key, connection):
    today_range = DateRange(int(resp_daterange.end / DAY) * DAY, int(resp_daterange.end))
    filename = '%s-%s-%s.json' % (options.project, options.type, today_range.filename_str())

    output_path = normpath(path_join(options.outputdir, filename))
    if not options.overwrite and path_exists(output_path):
        if not options.silent:
            # Confirm skip as does not make sense to request today's data just to skip overwriting it locally
            log('Overwriting is disabled. Are you sure you want to skip overwriting today\'s downloaded log? ' \
                '(Press \'y\' to skip or \'n\' to overwrite)')
            skip_options = ['y', 'n']
            for attempt in xrange(1, 4):  # default to skip after three bad attempts
                log('', new_line=False)
                skip = stdin.readline().strip().lower()
                if skip in skip_options:
                    break
                error('Please answer with \'y\' or \'n\'. (Attempt %d of 3)' % attempt)

            if 'n' != skip:
                warning('Skipping overwriting today\'s downloaded file: %s' % output_path)
                return
            else:
                warning('Overwrite disabled but overwriting today\'s downloaded file: %s' % output_path)
        else:   # Do not ask in silent mode, default to the option passed
            return

    if array_files_list:
        if options.verbose:
            log('Patching today\'s log file to include array events')

        if connection:
            today_log = inline_array_events_s3(options, today_log, array_files_list, enc_key, connection)
        else:
            today_log = inline_array_events_local(options, today_log, array_files_list, enc_key)

    write_to_file(options, today_log, filename=filename, output_path=output_path, force_overwrite=True)


# pylint: disable=E1103
def main():
    options = _parse_args()

    silent = options.silent
    if not silent:
        log('Downloading \'%s\' to %s.' % (options.type, options.outputdir or 'current directory'))

    try:
        r_data = _request_data(options)
        try:
            response_daterange = DateRange(r_data['start_time'], r_data['end_time'])

            datatype = options.type
            if 'users' == datatype:
                user_data = r_data['user_data']
            else: # if 'events' == datatype
                logs_url = r_data['logs_url']
                files_list = r_data['files_list']
                array_files_list = r_data['array_files_list']
                enc_key = r_data['key']
                if enc_key is not None:
                    # enc_key can be a unicode string and we need a stream of ascii bytes
                    enc_key = urlsafe_b64decode(enc_key.encode('ascii'))
                today_log = r_data['today_log']
        except KeyError as e:
            error('Missing information in response: %s' % e)
            exit(-1)
        del r_data

        daterange = options.daterange
        if not silent:
            if response_daterange.start != daterange.start:
                warning('Start date used (%s) not the same as what was specified (%s)' % \
                        (response_daterange.start_str, daterange.start_str))
            if response_daterange.end != daterange.end:
                warning('End date used (%s) not the same as what was specified (%s)' % \
                        (response_daterange.end_str, daterange.end_str))
            options.daterange = response_daterange

        output_dir = options.outputdir
        if output_dir and not path_exists(output_dir):
            # Not allowing creation of nested directories as greater chance of typos and misplaced files
            mkdir(output_dir)

        if 'users' == datatype:
            write_to_file(options, user_data)

        else: # if 'events' == datatype
            connection = None
            if logs_url and (files_list or array_files_list):
                connection = connection_from_url(logs_url, timeout=8.0)

            if files_list:
                if logs_url:
                    get_log_files_s3(options, files_list, enc_key, connection)
                else:
                    get_log_files_local(options, files_list, enc_key)
                del files_list

            if response_daterange.end > TODAY_START:
                # Patch and write, if requested, today's log with the array events downloaded and inlined
                patch_and_write_today_log(options, response_daterange, today_log, array_files_list, enc_key, connection)
                del today_log
                del array_files_list

        if not silent:
            log('Export completed successfully')

    except KeyboardInterrupt:
        if not silent:
            warning('Program stopped by user')
        exit(-1)
    except OSError as e:
        error(str(e))
        exit(-1)
    except Exception as e:
        error(str(e))
        exit(-1)

    return 0
# pylint: enable=E1103


if __name__ == "__main__":
    exit(main())
