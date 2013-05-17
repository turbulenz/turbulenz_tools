#!/usr/bin/env python
# Copyright (c) 2012-2013 Turbulenz Limited

from logging import basicConfig, CRITICAL, INFO, WARNING

from optparse import OptionParser, TitledHelpFormatter
from urllib3 import connection_from_url
from urllib3.exceptions import HTTPError, SSLError
from simplejson import loads as json_loads, dump as json_dump
from gzip import GzipFile
from zlib import decompress as zlib_decompress
from time import strptime, strftime, gmtime, mktime
from re import compile as re_compile
from sys import stdin
from os import mkdir
from os.path import exists as path_exists, join as path_join, normpath
from getpass import getpass, GetPassWarning
from base64 import urlsafe_b64decode
from Crypto.Cipher.AES import new as aes_new, MODE_CBC

from turbulenz_tools.tools.stdtool import standard_output_version

__version__ = '2.0.0'
__dependencies__ = []


HUB_COOKIE_NAME = 'hub'
HUB_URL = 'https://hub.turbulenz.com/'

DATATYPE_DEFAULT = 'events'
DATATYPE_URL = { 'events': '/dynamic/project/%s/event-log',
                 'users': '/dynamic/project/%s/user-info' }

DATE_FORMAT = '%Y-%m-%d'
DATERANGE_DEFAULT = strftime(DATE_FORMAT, gmtime())
DAY = 86400

# pylint: disable=C0301
USERNAME_PATTERN = re_compile('^[a-z0-9]+[a-z0-9-]*$') # usernames
PROJECT_SLUG_PATTERN = re_compile('^[a-zA-Z0-9\-]*$') # game
# pylint: enable=C0301


def log(message, new_line=True):
    print '\r >> %s' % message,
    if new_line:
        print

def error(message):
    log('[ERROR]   - %s' % message)

def warning(message):
    log('[WARNING] - %s' % message)


def _create_parser():
    usage = "usage: %prog [options] project"
    parser = OptionParser(description='Export event logs and anonymised user information of a game.',
                          usage=usage, formatter=TitledHelpFormatter())

    parser.add_option("--version", action="store_true", dest="output_version", default=False,
                      help="output version number")
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False, help="verbose output")
    parser.add_option("-s", "--silent", action="store_true", dest="silent", default=False, help="silent running")

    parser.add_option("-u", "--user", action="store", dest="user",
                      help="Hub login username (will be requested if not provided)")
    parser.add_option("-p", "--password", action="store", dest="password",
                      help="Hub login password (will be requested if not provided)")

    parser.add_option("-t", "--type", action="store", dest="datatype", default=DATATYPE_DEFAULT,
                      help="type of data to download, either events or users (defaults to " + DATATYPE_DEFAULT + ")")
    parser.add_option("-d", "--daterange", action="store", dest="daterange", default=DATERANGE_DEFAULT,
                      help="individual 'yyyy-mm-dd' or range 'yyyy-mm-dd : yyyy-mm-dd' of dates to get the data for " \
                           "(defaults to today)")
    parser.add_option("-o", "--outputdir", action="store", dest="outputdir",
                      help="folder to output the downloaded files to (defaults to current directory)")
    #use json2json for this
    #parser.add_option("-m", "--merge", action="store", dest="outputfilename",
    #                  help="if the data to be downloaded is across multiple files, merge it into one file")

    parser.add_option("-w", "--overwrite", action="store_true", dest="overwrite", default=False,
                      help="if a file to be downloaded exists in the output directory, " \
                           "overwrite instead of skipping it")

    parser.add_option("--indent", action="store_true", dest="indent", default=False,
                      help="apply indentation to the JSON output")

    parser.add_option("--hub", action="store", dest="hub", default=HUB_URL,
                      help="Hub url (defaults to https://hub.turbulenz.com/)")

    return parser


def _check_options():
    parser = _create_parser()
    (options, args) = parser.parse_args()

    if options.output_version:
        standard_output_version(__version__, __dependencies__, None)
        exit(0)

    if options.silent:
        basicConfig(level=CRITICAL)
    elif options.verbose:
        basicConfig(level=INFO)
    else:
        basicConfig(level=WARNING)

    if 0 == len(args):
        error('Hub project required')
        exit(1)
    if 1 < len(args):
        error('Too many arguments. Please provide the slug of the project you wish to download from')
        exit(1)
    project = args[0]
    options.project = project

    if not PROJECT_SLUG_PATTERN.match(project):
        error('Incorrect "project" format')
        exit(-1)

    username = options.user
    if not username:
        print 'Username: ',
        username = stdin.readline()
        if not username:
            error('Login information required')
            exit(-1)
        username = username.strip()
        options.user = username

    if not USERNAME_PATTERN.match(username):
        error('Incorrect "username" format')
        exit(-1)

    if not options.password:
        try:
            options.password = getpass()
        except GetPassWarning:
            error('Echo free password entry unsupported. Please provide a --password argument')
            return -1

    if options.datatype not in ['events', 'users']:
        error('Type must be one of \'events\' or \'users\'')
        exit(1)

    daterange = options.daterange.replace(':', ' ').split()

    if len(daterange) < 1:
        error('Date not set')
        exit(1)
    elif len(daterange) > 2:
        error('Can\'t provide more than two dates for date range')
        exit(1)

    try:
        for d in daterange:
            strptime(d, DATE_FORMAT)
    except ValueError:
        error('Dates must be in the yyyy-mm-dd format')
        exit(1)

    if daterange[0] > daterange[-1]:
        error('Start date can\'t be greater than the end date')
        exit(1)

    options.daterange = daterange

    if not options.hub:
        options.hub = 'http://127.0.0.1:8080'

    if not options.outputdir:
        options.outputdir = ''

    return options


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
    params = { 'start_time': int(mktime(strptime(daterange[0] + ' GMT', DATE_FORMAT + ' %Z'))),
               'end_time': int(mktime(strptime(daterange[-1] + ' GMT', DATE_FORMAT + ' %Z'))),
               'version': __version__ }

    connection = connection_from_url(options.hub, timeout=8.0)
    cookie = login(connection, options)

    try:
        r = connection.request('GET',
                               DATATYPE_URL[options.datatype] % options.project,
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
        start_date = options.daterange[0]
        end_date = options.daterange[-1]

        filename = '%s-%s-%s' % (options.project, options.datatype, start_date)
        if start_date != end_date:
            filename += '_-_' + end_date
        filename += '.json'

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
        for index, filename in enumerate(array_files_list):
            # Format: 'eventlogspath/gamefolder/arrayevents/date(seconds)/objectid.bin'
            # The objectid doesn't correspond to a database entry but is used for uniqueness and timestamp

            event_objectid = filename.rsplit('/', 1)[-1].split('.', 1)[0]
            timestamp = get_objectid_timestamp(event_objectid)
            formatted_timestamp = strftime('%Y-%m-%d %H:%M:%S', gmtime(timestamp))

            if verbose:
                log('Retrieving array event ' + str(index + 1) + ' occuring at ' + formatted_timestamp)

            with open(filename, 'rb') as fin:
                file_content = fin.read()
            file_content = decrypt_data(file_content, enc_key)
            file_content = json_loads(zlib_decompress(file_content))

            slug = file_content['slug']
            del file_content['slug']
            file_content['time'] = formatted_timestamp

            if slug not in today_log:
                today_log[slug] = { 'playEvents': [], 'customEvents': [] }

            today_log[slug]['customEvents'].append(file_content)
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
                log('Requesting array event ' + str(index + 1) + ' occuring at ' + formatted_timestamp)
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

            slug = r_data['slug']
            del r_data['slug']
            r_data['time'] = formatted_timestamp

            if slug not in today_log:
                today_log[slug] = { 'playEvents': [], 'customEvents': [] }

            today_log[slug]['customEvents'].append(r_data)
            # Maintaining a list of slugs to sort the customEvents by date for so that added array events appear in
            # order but we do not unneccesarily sort large lists if an array event wasn't added to it
            to_sort.add(slug)

        for slug in to_sort:
            today_log[slug]['customEvents'].sort(key=lambda k: k['time'])

        return today_log

    except (HTTPError, SSLError) as e:
        error(e)
        exit(-1)


def patch_and_write_today_log(options, today_log, array_files_list, enc_key, connection):
    filename = '%s-%s-%s.json' % (options.project, options.datatype, options.daterange[-1])

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
    options = _check_options()

    silent = options.silent
    if not silent:
        log('Downloading \'%s\' to %s.' % (options.datatype, options.outputdir or 'current directory'))

    try:
        r_data = _request_data(options)
        try:
            start_date = strftime('%Y-%m-%d', gmtime(r_data['start_time']))
            end_date = strftime('%Y-%m-%d', gmtime(r_data['end_time']))
            datatype = options.datatype
            if 'users' == datatype:
                user_data = r_data['user_data']
            else: # if 'events' == datatype
                logs_url = r_data['logs_url']
                files_list = r_data['files_list']
                array_files_list = r_data['array_files_list']
                enc_key = urlsafe_b64decode(r_data['key'])
                today_log = r_data['today_log']
        except KeyError as e:
            error('Missing information in response: %s' % e)
            exit(-1)
        del r_data

        daterange = options.daterange
        if not silent:
            if start_date != daterange[0]:
                warning('Start date used (%s) not the same as what was specified (%s)' % (start_date, daterange[0]))
                options.daterange[0] = start_date
            if end_date != daterange[-1]:
                warning('End date used (%s) not the same as what was specified (%s)' % (end_date, daterange[-1]))
                options.daterange[1] = end_date

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

            if end_date == DATERANGE_DEFAULT:   # today
                # Patch and write, if requested, today's log with the array events downloaded and inlined
                patch_and_write_today_log(options, today_log, array_files_list, enc_key, connection)
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
