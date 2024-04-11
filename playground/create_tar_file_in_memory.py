#!/usr/bin/env python
import io
import tarfile
import time

target_file = io.BytesIO()

file1 = io.BytesIO()
content_file1 = 'Hi there\nNew line\n'.encode('utf-8')
file1.write(content_file1)
file1.seek(0)

tar = tarfile.open(fileobj=target_file, mode='w:xz')

info1 = tarfile.TarInfo()
info1.name = 'subdir/File1.txt'
info1.mtime = time.time()
info1.size = len(content_file1)
info1.type = tarfile.REGTYPE

tar.addfile(info1, file1)
tar.close()

target_file.seek(0)
print('Reading tar file from memory:')
print(
    target_file.read()
)
with open('test.tar.xz', 'wb') as fid:
    target_file.seek(0)
    fid.write(target_file.read())
# extract with tar xvJf test.tar.xz


## Reading
tar = tarfile.open(fileobj=target_file, mode='r')
