#!/usr/bin/env python3

import argparse
import sys

from .cli.coap_air_cli import CoAPAirCli
from .cli.http_air_cli import HTTPAirCli
from .cli.v_107_cli import Version107Cli


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--ipaddr', help='IP address of air purifier')
    parser.add_argument('--version', help='set the version of your device ', choices=['0.1.0','0.2.1', '1.0.7'], default='0.1.0')
    parser.add_argument('-d', '--debug', help='show debug output', action='store_true')
    parser.add_argument('--om', help='set fan speed', choices=['1','2','3','s','t'])
    parser.add_argument('--pwr', help='power on/off', choices=['0','1'])
    parser.add_argument('--mode', help='set mode', choices=['P','A','S','M','B','N'])
    parser.add_argument('--rhset', help='set target humidity', choices=['40','50','60','70'])
    parser.add_argument('--func', help='set function', choices=['P','PH'])
    parser.add_argument('--aqil', help='set light brightness', choices=['0','25','50','75','100'])
    parser.add_argument('--uil', help='set button lights on/off', choices=['0','1'])
    parser.add_argument('--ddp', help='set indicator pm2.5/IAI/Humidity', choices=['0','1','3'])
    parser.add_argument('--dt', help='set timer', choices=['0','1','2','3','4','5','6','7','8','9','10','11','12'])
    parser.add_argument('--cl', help='set child lock', choices=['True','False'])
    parser.add_argument('--wifi', help='read wifi options', action='store_true')
    parser.add_argument('--wifi-ssid', help='set wifi ssid')
    parser.add_argument('--wifi-pwd', help='set wifi password')
    parser.add_argument('--firmware', help='read firmware', action='store_true')
    parser.add_argument('--filters', help='read filters status', action='store_true')
    args = parser.parse_args()

    if args.ipaddr:
        devices = [ {'ip': args.ipaddr} ]
    else:
        if args.version in [ '0.2.1', '1.0.7']:
            print('Autodetection is not supported when using CoAP. Use --ipaddr to set an IP address.')
            sys.exit(1)

        devices = HTTPAirCli.ssdp(debug=args.debug)
        if not devices:
            print('Air purifier not autodetected. Try --ipaddr option to force specific IP address.')
            sys.exit(1)

    for device in devices:
        if args.version == '0.1.0':
            c = HTTPAirCli(device['ip'])
            c.load_key()
        elif args.version == '0.2.1':
            c = CoAPAirCli(device['ip'])
        elif args.version == '1.0.7':
            c = Version107Cli(device['ip'], debug=args.debug)

        if args.wifi:
            c.get_wifi()
            sys.exit(0)
        if args.firmware:
            c.get_firmware()
            sys.exit(0)
        if args.wifi_ssid or args.wifi_pwd:
            c.set_wifi(args.wifi_ssid, args.wifi_pwd)
            sys.exit(0)
        if args.filters:
            c.get_filters()
            sys.exit(0)

        values = {}
        if args.om:
            values['om'] = args.om
        if args.pwr:
            values['pwr'] = args.pwr
        if args.mode:
            values['mode'] = args.mode
        if args.rhset:
            values['rhset'] = int(args.rhset)
        if args.func:
            values['func'] = args.func
        if args.aqil:
            values['aqil'] = int(args.aqil)
        if args.ddp:
            values['ddp'] = args.ddp
        if args.uil:
            values['uil'] = args.uil
        if args.dt:
            values['dt'] = int(args.dt)
        if args.cl:
            values['cl'] = (args.cl == 'True')

        if values:
            c.set_values(values, debug=args.debug)
        else:
            c.get_status(debug=args.debug)


if __name__ == '__main__':
    main()
