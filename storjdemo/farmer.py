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


import logging
import json
import base64
import pickle
import sys
import time
import hashlib  # For SHA-256 Encoding
import binascii
import os
import os.path

from heartbeat import Swizzle
from storj.messaging import ChannelHandler
from storj.messaging import StorjTelehash
from storjutp.storjutp import Storjutp

log_fmt = '%(filename)s:%(lineno)d %(funcName)s() %(message)s'
logging.basicConfig(level=logging.DEBUG, format=log_fmt)

ERROR = -1
FINISHED = 99
# Never be '.' if farmer.py and uploader.py run simultaneously.
DOWNLOAD_PATH = './download/'
telehash = None
status = 0
stop = False


def get_hash(f):
    """
    get a hash.
    :param bytes f: byte data to be hashed
    :return: hash
    """
    m = hashlib.sha256()
    m.update(f)
    sha = m.digest()
    return sha


class FarmerHandler(ChannelHandler):

    """
    class for openining and handlinkg farming channel of uploader
    for farming.
    """

    def __init__(self):
        """
        init
        """
        ChannelHandler.__init__(self)
        self.file_info = {}

    def seqAA_request(self, packet):
        """
        request a file. send a telehash location.

        :param str packet: recieved packet, None due to opening.
        :return: telehash location
        """
        global telehash
        logging.info("requesting a file...")
        rpacket = {}
        rpacket['telehash_location'] = telehash.get_my_location()
        return json.dumps(rpacket)

    def seqAB_accept_file(self, packet):
        """
        accept a file information.
        register file hash, tag hash for heartbeat, and send acceptable
        utp ip address and port number, and start downloading.

        :param str packet: recieved packet, including hash of file and
                           hash of heartbeat tag.
        :return: json str, including utp ip address and
                  utp port.
        """
        logging.info("accepting file hashes...")
        rpacket = {}

        p = json.loads(packet)
        self.file_finished = 0
        self.file_hash = binascii.unhexlify(p['file_hash'])
        self.tag_hash = binascii.unhexlify(p['tag_hash'])
        logging.info('accepting file %s and tag_hash %s'
                     % (self.file_hash, self.tag_hash))
        self.utp = Storjutp()
        self.utp.regist_hash(self.file_hash, self.handler, DOWNLOAD_PATH)
        self.utp.regist_hash(self.tag_hash, self.handler, DOWNLOAD_PATH)
        loc = json.loads(telehash.get_my_location())
        rpacket['utp_ip'] = loc['paths'][0]['ip']
        rpacket['utp_port'] = self.utp.get_serverport()
        return json.dumps(rpacket)

    def seqAC_report_downloaded(self, packet):
        """
        wait finishing it and report of finishing it.

        :param str packet: recieved packet, including public beat
        :return: json str, only including success or not
        """
        logging.info("reoprt that downloaded a file...")
        rpacket = {}
        p = json.loads(packet)
        public_beat = Swizzle.Swizzle.fromdict(p['public_beat'])
        while self.file_finished != FINISHED and\
                self.file_finished != ERROR:
            time.sleep(1)
        logging.info("finished downloading...")
        self.utp.stop_hash(self.file_hash)
        self.utp.stop_hash(self.tag_hash)
        if self.file_finished == FINISHED:
            self.file_info['public_beat'] = public_beat
            self.file_info['tag'] = DOWNLOAD_PATH +\
                binascii.hexlify(self.tag_hash).decode().upper()
            self.file_info['file'] = DOWNLOAD_PATH +\
                binascii.hexlify(self.file_hash).decode().upper()
            return '{"success":1}'
        return '{"success":0}'

    def handler(self, hash, error):
        """
        handler when finishng downloading.
        check a file hash is same as one informed from uploader.

        :param byte hash: file hash that was finished downloading.
        :param str err: error info , None if no error.
        """
        if error is not None:
            logging.error("downloaded failed..." + error)
        else:
            fname = DOWNLOAD_PATH + binascii.hexlify(hash).upper().decode()
            with open(fname, 'rb') as f:
                b = f.read()
                hash_ = get_hash(b)
            if hash_ != hash:
                logging.error("downloaded file is corrupted...")
                self.file_finished = ERROR
                return
            self.file_finished += 1
            if self.file_finished < 2:
                return
            self.file_finished = FINISHED

    def factory(self):
        """
        factory for accepting a heart beat channel.
        """
        if self.file_info != {}:
            return FarmerHeartbeatHandler(self.file_info)
        return None


class FarmerHeartbeatHandler(ChannelHandler):

    """
    class for accepting heartbeat channel.
    """

    def __init__(self, file_info):
        """
        init
        """
        ChannelHandler.__init__(self)
        self.file_info = file_info
        pass

    def seqAA_make_proof(self, packet):
        """
        make a proof.
        accept chanlleng, make a tag from the downloaded file, and make
        a proof.

        :param str packet: received json str, including challenge.
        :return: return json str, including proof
        """
        logging.info("making proof...")
        rpacket = {}
        p = json.loads(packet)
        cha = Swizzle.Swizzle.challenge_type().fromdict(p['challenge'])
        with open(self.file_info['tag'], 'rb') as file:
            decoded = base64.b64encode(file.read()).decode('ascii')
        tag = Swizzle.Swizzle.tag_type().fromdict(decoded)
        with open(self.file_info['file'], 'rb') as file:
            proof = self.file_info['public_beat'].prove(file, cha, tag)
        rpacket['proof'] = proof.todict()
        return json.dumps(rpacket)

    def seqAB_get_result(self, packet):
        """
        receive a verification result.

        :param str packet: received json str, including verification result.
        :return: None to close channel.
        """
        logging.info("receiving result...")
        p = json.loads(packet)
        if not p['valid']:
            logging.info("proof failed...")
            status = ERROR
        else:
            logging.info("proof succeed....")
        return None


def set_stop_flag(flag):
    global stop
    stop = flag


def main(destination):
    global telehash
    global stop
    global status

    if not os.path.exists(DOWNLOAD_PATH):
        os.mkdir(DOWNLOAD_PATH)
    telehash = StorjTelehash(-9999)

    f = FarmerHandler()
    logging.info('starting to open a farming channel at ' +
                 telehash.get_my_location())
    telehash.open_channel(destination, 'farming', f)
    logging.info('starting to listen heartbeat channel')
    telehash.add_channel_handler('heartbeat', f.factory)

    while status == 0 and not stop:
        time.sleep(10)

    if status == ERROR:
        logging.error("something wrong")
        return 1

    return 0

if __name__ == '__main__':
    main(sys.argv[1])
