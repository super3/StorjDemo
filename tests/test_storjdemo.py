# -*- coding: utf-8 -*-

# Copyright (c) 2015, Shinya Yagyu
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
# 3. Neither the name of the copyright holder nor the names of its contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.


import pytest
import time
import logging
import filecmp
import os
import threading
import hashlib
import binascii

import storjdemo

log_fmt = '%(filename)s:%(lineno)d %(funcName)s() %(message)s'
logging.basicConfig(level=logging.DEBUG, format=log_fmt)

FILENAME = 'storjdemo/rand.dat'


class TestStorjDemo(object):

    def test_storjutp(self):
        id = (
              '{"hashname":'
              '"hgpcqahkrfo3u7zwwfyvr6gyfphw2xes2vryo7up2fwtekjkag6a",'
              '"keys":{"1a":"apqnpze5tlbpdrafud3e4onjxdwar2t6oi"},'
              '"secrets":{"1a":"3stkh7snnk7hkcxnkoe2g2ax66ik4tr3"}}'
              )
        dest = (
                '{"keys":{"1a":"apqnpze5tlbpdrafud3e4onjxdwar2t6oi"},'
                '"paths":[{"type":"udp4","ip":"127.0.0.1","port":9999}]}'
                )

        downloaded_file = (
            'download/'
            'B582CD086064205A35B561B3FD6E67E79BF61F568A5F8BA2367E1F7DBB1DEDA4'
            )
        with open('id.json', 'w') as file:
            file.write(id)

        with open(FILENAME, 'rb') as file:
            m = hashlib.sha256()
            m.update(file.read())
            downloaded_file = 'download/' +\
                binascii.hexlify(m.digest()).decode().upper()

        f = threading.Thread(
            target=storjdemo.uploader.main, args=(9999,))
        f.start()
        u = threading.Thread(
            target=storjdemo.farmer.main, args=(dest,))
        u.start()

        time.sleep(5)
        storjdemo.uploader.set_stop_flag(True)
        storjdemo.farmer.set_stop_flag(True)
        f.join()
        u.join()

        assert os.path.exists(downloaded_file)
        assert storjdemo.farmer.status == 0
        assert storjdemo.uploader.status == 0
        assert filecmp.cmp(FILENAME, downloaded_file)
