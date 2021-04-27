[![Build Status](https://travis-ci.org/rgerganov/py-air-control.svg?branch=master)](https://travis-ci.org/rgerganov/py-air-control)
[![PyPI version](https://badge.fury.io/py/py-air-control.svg)](https://badge.fury.io/py/py-air-control)

Command line application for controlling Philips air purifiers.
Supports devices communicating over HTTP, CoAP and encrypted CoAP.

Installation
---
Python 3.4+ is required. Install with `pip3`:
```
$ pip3 install py-air-control
```
If your device is using CoAP then update the `CoAPthon3` dependency to get fixes for several known bugs:
```
$ pip3 install -U git+https://github.com/rgerganov/CoAPthon3
```

Wi-Fi setup
---
The purifier can be connected to a Wi-Fi network with the following steps:

 1. Put the purifier into pairing mode. On AC2729 this is done by holding the power and child-lock buttons for 3 seconds.
    The purifier will create an open "PHILIPS Setup" wi-fi network.
 2. Connect your PC to the "PHILIPS Setup" network and get IP settings via DHCP. The IP address of the purifier will be 192.168.1.1.
 3. Now you can re-configure the wi-fi network of the purifier like this:
```
airctrl --ipaddr 192.168.1.1 --wifi-ssid <your_wifi_ssid> --wifi-pwd <your_wifi_password>
```
_Note: this feature is only available for devices that work over HTTP_

Usage in the local network
---
Getting the current status of device with IP 192.168.0.17:
```
$ airctrl --ipaddr 192.168.0.17
[pwr]   Power: ON
[pm25]  PM25: 4
[rh]    Humidity: 32
[rhset] Target humidity: 60
[iaql]  Allergen index: 1
[temp]  Temperature: 22
[func]  Function: Purification & Humidification
[mode]  Mode: M
[om]    Fan speed: 2
[aqil]  Light brightness: 100
[wl]    Water level: 100
[cl]    Child lock: False
```
You don't have to specify the IP address (--ipaddr parameter) if there is only one device in your LAN or you want to send commands to all your devices.
The IP address will be autodetected using SSDP (UPnP) if the UDP 1900 port is not blocked.

You can change settings by using the prefix in the square brackets as a command line option.
For example to set fan speed 2:

    $ airctrl --om 2

For AC2889 you may need to specify both manual mode *and* fan speed:

    $ airctrl --mode M --om 2

Set target humidity to 50%:

    $ airctrl --rhset 50

Change function to "Purification":

    $ airctrl --func P

Power off the device:

    $ airctrl --pwr 0

and so on

To get filters status:
```
$ airctrl --filters
Pre-filter and Wick: clean in 245 hours
Wick filter: replace in 3965 hours
Active carbon filter: replace in 1565 hours
HEPA filter: replace in 3965 hours
```

Switching the the communication protocol
---
Use --protocol to switch between communication protocols.
The following command will try to retrieve the current status using the CoAP protocol with encryption:
```
$ airctrl --ipaddr 192.168.0.17 --protocol coap
```

The following command will try to retrieve the current status using the CoAP protocol without encryption:
```
$ airctrl --ipaddr 192.168.0.17 --protocol plain_coap
```

Running without root privileges (Plain CoAP protocol only)
---
_Works since Linux kernel 2.6.39._

Use id command to query your group ID:
```
$ id -g
995
```

The following command set the range of group IDs that are allowed to create ICMP sockets (ping_group_range kernel parameter, the default is "1 0", which means no group is allowed to create ICMP Echo sockets):
```
$ sudo sysctl -w net.ipv4.ping_group_range="0 1000"
net.ipv4.ping_group_range = 0 1000
```

Make it permanent:
```
$ echo "net.ipv4.ping_group_range=0 1000" | sudo tee -a /etc/sysctl.conf
$ sudo sysctl -p
net.ipv4.ping_group_range = 0 1000
``` 
(see also: https://man7.org/linux/man-pages/man7/icmp.7.html)


Output of different devices
---
- For further examples click [here](Examples.md)

Usage via cloud services
---
Use the `cloudctrl` script to control your device via the Philips cloud.

First you need to find your device id, provision an account and pair the account with the device id:
```
$ airctrl --ipaddr 192.168.0.17 --wifi
{'cppid': '9dcc618e9a82045d',
...
$ cloudctrl 9dcc618e9a82045d --pair 192.168.0.17
Creating cloud account ...
Logging in with 000000fff0000019
Client id: 000000fff10d40a1
Client key: NrIBL02WJNFDICqR6FGKig==
Exchanging secret key with the device ...
Saving session_key 512735aa3a5dc2608dfa8997b1b03a29 to /home/rgerganov/.pyairctrl
Pairing with 192.168.0.17 ...
{'return': [0]}
Logging in with 000000fff10d40a1
Sending pair request to cloud service ...
Relationship status: completed
```
The pairing needs to be done only once for each device, in the local network of the device.


Then you can control the paired device over the internet by using its ID and the account saved in `~/.pyairctrl`:
```
$ cloudctrl 9dcc618e9a82045d --pwr 1
Logging in with 000000fff10d40a1
Sending event {'pwr': '1'} to device with id 9dcc618e9a82045d
```

_Note: all IDs and credentials above are randomly generated and only used for illustration purposes_
_Note: this feature is only available for devices that work over HTTP_
