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

from heartbeat import Swizzle
from storj.messaging import ChannelHandler
from storj.messaging import StorjTelehash
from storjutp.storjutp import Storjutp

log_fmt = '%(filename)s:%(lineno)d %(funcName)s() %(message)s'
logging.basicConfig(level=logging.DEBUG, format=log_fmt)

FILENAME = 'rand.dat'
ERROR = -1
FINISHED = 99

beat = Swizzle.Swizzle()
status = 0

def get_hash(f):
    m = hashlib.sha256()
    m.update(f)
    sha = m.digest()
    return sha

def prepare_heartbeat(filename):
    with open(filename, 'rb') as file:
        (tag_, state_) = beat.encode(file)
    state = state_.todict()
    tag = base64.b64decode(tag_.todict())
    h = get_hash(tag)
    with open(binascii.hexlify(h).upper(), 'wb') as f:
        f.write(tag)
    return (state, h)

def schedule_heartbeat(sl, state):
    time.sleep(sl)
    t.open_channel(self.destination, 'heartbeat', 
    UploaderHeartbeatHandler(state))

class UploaderHandler(ChannelHandler):
    def __init__(self, t):
        ChannelHandler.__init__(self)
        self.telehash = t
        with open(FILENAME, 'rb') as f:
            self.hash = get_hash(f.read())

    def seqAA_accept_request(self, packet):
        logging.info("accepting request a file...")
        rpacket = {}
        p = json.loads(packet)
        self.destination = p['telehash_location']
        self.dest_utp_ip = p['utp_ip']
        self.dest_utp_port = p['utp_port']
        rpacket['file_hash'] = \
            binascii.hexlify(self.hash).upper().decode()
        (self.state, self.tag_hash) =prepare_heartbeat(FILENAME)
        self.tag_hash_hex =\
            binascii.hexlify(self.tag_hash).upper().decode()
        rpacket['tag_hash'] = self.tag_hash_hex
        logging.info('sending file %s and tag_hash %s'
                      % (rpacket['tag_hash'] ,rpacket['file_hash']))
        return json.dumps(rpacket)

    def seqAB_send_file(self, packet):
        logging.info("sending file...")
        self.utp = Storjutp()
        self.utp.send_file(self.dest_utp_ip, self.dest_utp_port, 
                           self.tag_hash_hex, 
                           self.tag_hash, self.handler)
        self.utp.send_file(self.dest_utp_ip, self.dest_utp_port, FILENAME,
                           self.hash, self.handler)
        return '{"success":1}'
        
    def seqAC_first_heartbeat(self, packet):
        logging.info("preparing heartbeat...")
        rpacket = {}
        p = json.loads(packet)
        if p['success'] :
            threading.Thread(target = schedule_heartbeat,
                             args = (0, self.state))
        return None

    def handler(self, hash, error):
        pass


class UploaderHeartbeatHandler(ChannelHandler):
    def __init__(self, state):
        ChannelHandler.__init__(self)
        self.state = state
        pass

    def seqAA_send_challenge(self, packet):
        rpakcet = {}
        self.cha = beat.gen_challenge(self.state)
        rpacket['challenge'] = self.cha.todict()
        return json.dumps(rpakcet)

    def seqAB_verify(self, packet):
        rpakcet = {}
        p = json.loads(packet)
        with open(fILENAME,'rb') as file:
            rpakcet['valid'] = \
                beat.verify(p['proof'], self.cha, self.state)
        if rpacket['valid']:
            threading.Thread(target = schedule_heartbeat,
                             args = (30, self.state))
        return json.dumps(rpakcet)

def main(port):
    t = StorjTelehash(port)
    logging.info('starting to listen a farming channel at ' +
                  t.get_my_location())
    t.add_channel_handler('farming', (lambda: UploaderHandler(t)))

    while status == 0:
        time.sleep(10);
    
    if status == ERROR:
        logging.error("something wrong")

if __name__ == '__main__':
    if len(sys.argv) > 1:
        port = sys.argv[1]
    else:
        port = 9999
    main(port)
