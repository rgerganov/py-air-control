Command line application for controlling Philips air purifiiers.

It is tested with AC2729 and AC2889 models but it should work with all purifiers made by Philips.

Installation
---
Python 3.4+ is required. Install with `pip3`:
```
$ pip3 install py-air-control
```

Wi-Fi setup
---
The purifier can be connected to a Wi-Fi network with the following steps:

 1. Put the purifier into pairing mode. On AC2729 this is done by holding the power and child-lock buttons for 3 seconds.
    The purifier will create an open "PHILIPS Setup" wi-fi network.
 2. Connect your PC to the "PHILIPS Setup" network and get IP settings via DHCP. The IP address of the purifier will be 192.168.1.1.
 3. Now you can re-configure the wi-fi network of the purifier like this:
```
airctrl 192.168.1.1 --wifi-ssid <your_wifi_ssid> --wifi-pwd <your_wifi_password>
```

Usage
---
Getting the current status of device with IP 192.168.0.17:
```
$ airctrl 192.168.0.17
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
You can change settings by using the prefix in the square brackets as a command line option.
For example to set fan speed 2:

    $ airctrl 192.168.0.17 --om 2

Set target humidity to 50%:

    $ airctrl 192.168.0.17 --rhset 50

Change function to "Purification":

    $ airctrl 192.168.0.17 --func P

Power off the device:

    $ airctrl 192.168.0.17 --pwr 0

and so on

To get filters status:
```
$ airctrl 192.168.0.17 --filters
Pre-filter and Wick: clean in 245 hours
Wick filter: replace in 3965 hours
Active carbon filter: replace in 1565 hours
HEPA filter: replace in 3965 hours
```
