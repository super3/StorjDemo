[![Build Status](https://travis-ci.org/StorjPlatform/StorjDemo.svg?branch=master)](https://travis-ci.org/StorjPlatform/StorjDemo)
[![Coverage Status](https://coveralls.io/repos/StorjPlatform/StorjDemo/badge.svg?branch=master)](https://coveralls.io/r/StorjPlatform/StorjDemo?branch=master)

# Farming Demo on Storj Platform

This program demonstrates:

Uploader:

1. listen requests to send a file by farmer by [StorjTelehash](https://github.com/StorjPlatform/StorjTelehash.git).
2. send a file and hearbeat information when requested by [Storjutp](https://github.com/StorjPlatform/Storjutp.git).
3. request and verify heartbeats periodically.

Farmer:

1. open a channel to request a file to a farmer by StorjTelehash.
2. receive a file and hearbeat information by Storjutp.
3. accept heartbeats and make proof periodically.

Document is [here](https://rawgit.com/StorjPlatform/StorjDemo/master/docs/html/index.html)

## Requirements
This requires 
* `g++` (v4.8 or higher for test)
* `python` (2.7.x ,3.3.x, or 3.4.x)

## Installation
Before installation, if you didn't install crypto++,

    $sudo apt-get install libcrypto++-dev libgmp-dev

To install the program,

    $ python setup.py install

To run the associated tests.

    $ PYTHONPATH=. py.test -q tests/test.py -s

### For Windows OS
For Windows OS, [Cygwin](https://www.cygwin.com/) must be installed first.

1. download cygwin installer from [here](https://www.cygwin.com/setup-x86.exe) and run it.
1. go forward to package selection, and select packages below, and go forward to install them.

under devel category:

1. gcc-g++
1. make
2. git

under Python category:

1. python
1. python3
1. python-setuptools
1. python3-setuptools

under libs category:

1. libevent2.0_5
1. libevent-devel
1. libgmp-devel

And you must install crypto++ by

    $ git clone https://github.com/cawka/cryptopp-cygwin.git
    $ cd cryptopp-cygwin
    $ make
    $ make install

After that run c:\cygwin\cygwin.bat and follow the installation section.


## Usage

First run uploader by

    $ python uploader.py

If you want to specify a port number (eg. 12345) listening channels, 

    $ python uploader.py 12345

Then, find the location from the output. If you find the output like

```
uploader.py:253 main() starting to listen a farming channel at {"hashname":"hgpcqahkrfo3u7zwwfyvr6gyfphw2xes2vryo7up2fwtekjkag6a","keys":{"1a":"apqnpze5tlbpdrafud3e4onjxdwar2t6oi"},"paths":[{"type":"udp4","ip":"127.0.0.1","port":9999}]}
```

then destination is 
```
{"hashname":"hgpcqahkrfo3u7zwwfyvr6gyfphw2xes2vryo7up2fwtekjkag6a","keys":{"1a":"apqnpze5tlbpdrafud3e4onjxdwar2t6oi"},"paths":[{"type":"udp4","ip":"127.0.0.1","port":9999}]}
```

And run farmer by

    $ python farmer.py <distination>

for example,

    $ python farmer.py '{"hashname":"hgpcqahkrfo3u7zwwfyvr6gyfphw2xes2vryo7up2fwtekjkag6a","keys":{"1a":"apqnpze5tlbpdrafud3e4onjxdwar2t6oi"},"paths":[{"type":"udp4","ip":"127.0.0.1","port":9999}]}'
    
Never forget to quote the destination with single quotation.

# Contribution
Improvements to the codebase and pull requests are encouraged.


