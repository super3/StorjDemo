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
import hashlib
import binascii
import threading

from heartbeat import Swizzle
from storj.messaging import ChannelHandler
from storj.messaging import StorjTelehash
from storjutp.storjutp import Storjutp

log_fmt = '%(filename)s:%(lineno)d %(funcName)s() %(message)s'
logging.basicConfig(level=logging.DEBUG, format=log_fmt)

FILENAME = 'storjdemo/rand.dat'
ERROR = -1
FINISHED = 99
HEARBEAT_INTARVAL = 10
beat = Swizzle.Swizzle()
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


def prepare_heartbeat(filename):
    """
    prepare heartbeat.
    encode a file , save tag to a file named by tag hash,
    and return state and a hash of tag.
    :param str filename: heartbeat target filename
    :return: state and a hash of tag
    """
    global beat
    with open(filename, 'rb') as file:
        (tag_, state) = beat.encode(file)
    tag = base64.b64decode(tag_.todict())
    h = get_hash(tag)
    with open(binascii.hexlify(h).upper(), 'wb') as f:
        f.write(tag)
    return (state, h)


class UploaderHandler(ChannelHandler):

    """
    class for handling farming channel for uploader
    """

    def __init__(self):
        """
        init
        """
        ChannelHandler.__init__(self)

    def seqAA_accept_request(self, packet):
        """
        accept a file request.
        send information about a hash of a file and a hearbeat tag,
        and public beat.

        :param str packet: received json packet, including
                           telehash location.
        :return: sending json packet, including hash of file and heartbeat
                  and tag to be sent.
        """
        logging.info("accepting request a file...")
        rpacket = {}
        p = json.loads(packet)
        self.destination = p['telehash_location']
        with open(FILENAME, 'rb') as f:
            self.file_hash = get_hash(f.read())
        rpacket['file_hash'] = \
            binascii.hexlify(self.file_hash).upper().decode()
        (self.state, self.tag_hash) = prepare_heartbeat(FILENAME)
        self.tag_hash_hex =\
            binascii.hexlify(self.tag_hash).upper().decode()
        rpacket['tag_hash'] = self.tag_hash_hex
        logging.info('sending file %s and tag_hash %s'
                     % (rpacket['file_hash'], rpacket['tag_hash']))
        return json.dumps(rpacket)

    def seqAB_send_file(self, packet):
        """
        send a file.
        send a file and a hearbeat tag,

        :param str packet: received json packet, including
                          utp ip address and port number.
        :return: sending json packet, including public heartbeat.
        """
        logging.info("sending file...")
        rpacket = {}
        p = json.loads(packet)
        dest_utp_ip = p['utp_ip']
        dest_utp_port = p['utp_port']
        utp = Storjutp()
        utp.send_file(dest_utp_ip, dest_utp_port,
                      self.tag_hash_hex,
                      self.tag_hash, self.handler)
        utp.send_file(dest_utp_ip, dest_utp_port, FILENAME,
                      self.file_hash, self.handler)
        rpacket['public_beat'] = beat.get_public().todict()
        return json.dumps(rpacket)

    def seqAC_first_heartbeat(self, packet):
        """
        accept a file downloaded report and prepare a haertbeat in a thread.

        :param str packet: received json packet, including
                           success flag..
        :return: sending json packet, None to close the channel.
        """
        logging.info("preparing heartbeat...")
        rpacket = {}
        p = json.loads(packet)
        if p['success']:
            logging.info("threading heartbeat...")
            t = threading.Thread(
                target=UploaderHeartbeatHandler.schedule_heartbeat,
                args=(1, self.state, self.destination))
            t.start()

        return None

    def handler(self, hash, error):
        """
        handler for uTP. For now do nothing.
        """
        pass


class UploaderHeartbeatHandler(ChannelHandler):

    """
    class for sending heartbeat channel.
    """

    def __init__(self, state, destination):
        """
        init
        """
        ChannelHandler.__init__(self)
        self.state = state
        self.destination = destination
        pass

    @classmethod
    def schedule_heartbeat(cls, sl, state, destination):
        """
        schedule a heartbeat in a thread.

        :param int s1: wait time before starting heartbeat.
        :param object state: heartbeat state
        :param str destination: telehash destination
        """
        global telehash
        logging.debug('starting heartbeat')
        time.sleep(sl)
        telehash.open_channel(destination, 'heartbeat',
                              UploaderHeartbeatHandler(state, destination))

    def seqAA_send_challenge(self, packet):
        """
        make and send a challenge.

        :param str packet: None
        :return: sending json packet, including challenge of heartbeat.
        """
        rpacket = {}
        self.cha = beat.gen_challenge(self.state)
        rpacket['challenge'] = self.cha.todict()
        return json.dumps(rpacket)

    def seqAB_verify(self, packet):
        """
        verify a proof.

        :param str packet: received json packet, including
                           proof of heartbeat.
        :return: sending json packet, including a result of verification.
        """
        rpacket = {}
        p = json.loads(packet)
        proof = Swizzle.Swizzle.proof_type().fromdict(p['proof'])
        rpacket['valid'] = \
            beat.verify(proof, self.cha, self.state)
        if rpacket['valid']:
            t = threading.Thread(
                target=UploaderHeartbeatHandler.schedule_heartbeat,
                args=(HEARBEAT_INTARVAL, self.state, self.destination))
            t.start()
        return json.dumps(rpacket)


def set_stop_flag(flag):
    global stop
    stop = flag


def main(port):
    global telehash
    global stop
    global status

    telehash = StorjTelehash(port)
    logging.info('starting to listen a farming channel at ' +
                 telehash.get_my_location())
    telehash.add_channel_handler('farming', (lambda: UploaderHandler()))

    while status == 0 and not stop:
        time.sleep(10)

    if status == ERROR:
        logging.error("something wrong")
        return 1

    return 0

if __name__ == '__main__':
    if len(sys.argv) > 1:
        port = sys.argv[1]
    else:
        port = 9999
    main(port)
