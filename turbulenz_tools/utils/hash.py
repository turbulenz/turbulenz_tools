# Copyright (c) 2010-2011,2013 Turbulenz Limited

from hashlib import md5, sha256
from base64 import urlsafe_b64encode

def hash_file_sha256_md5(file_path):
    file_obj = open(file_path, 'rb')
    ctx_sha256 = sha256()
    ctx_md5 = md5()
    x = file_obj.read(65536)
    while x:
        ctx_sha256.update(x)
        ctx_md5.update(x)
        x = None
        x = file_obj.read(65536)
    file_obj.close()
    file_sha256 = urlsafe_b64encode(ctx_sha256.digest()).rstrip('=')
    file_md5 = ctx_md5.hexdigest()
    return file_sha256, file_md5

def hash_file_sha256(file_path):
    file_obj = open(file_path, 'rb')
    ctx = sha256()
    x = file_obj.read(65536)
    while x:
        ctx.update(x)
        x = None
        x = file_obj.read(65536)
    file_obj.close()
    return urlsafe_b64encode(ctx.digest()).rstrip('=')

def hash_file_md5(file_path):
    file_obj = open(file_path, 'rb')
    ctx_md5 = md5()
    x = file_obj.read(65536)
    while x:
        ctx_md5.update(x)
        x = None
        x = file_obj.read(65536)
    file_obj.close()
    return ctx_md5.hexdigest()

def hash_for_file(file_name):
    return urlsafe_b64encode(hash_file_md5(file_name)).strip('=')

def hash_for_string(string):
    return urlsafe_b64encode(md5(string).digest()).strip('=')
