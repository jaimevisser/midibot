import hashlib
import sys


BUF_SIZE = 65536  # lets read stuff in 64kb chunks!


def hash(file:str) -> str: 
    md5 = hashlib.md5()

    with open(file, 'rb') as f:
        while True:
            data = f.read(BUF_SIZE)
            if not data:
                break
            md5.update(data)

    return md5.hexdigest()