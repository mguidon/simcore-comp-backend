""" Basic configuration file for S3

"""
from os import environ as env

S3_ENDPOINT = env.get("S3_ENDPOINT", "")
S3_ACCESS_KEY = env.get("S3_ACCESS_KEY", "")
S3_SECRET_KEY = env.get("S3_SECRET_KEY", "")
S3_BUCKET_NAME = env.get("S3_BUCKET_NAME", "")

class Config():
    def __init__(self):
        self._endpoint = S3_ENDPOINT
        self._access_key = S3_ACCESS_KEY
        self._secret_key = S3_SECRET_KEY
        self._bucket_name = S3_BUCKET_NAME
    
    @property
    def endpoint(self):
        return self._endpoint
    
    @property
    def access_key(self):
        return self._access_key
    
    @property
    def secret_key(self):
        return self._secret_key

    @property
    def bucket_name(self):
        return self._bucket_name