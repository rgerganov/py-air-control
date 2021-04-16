#!/usr/bin/env python3

import argparse
import sys
import pprint

from pyairctrl.status_transformer import STATUS_TRANSFORMER
from pyairctrl.coap_client import CoAPAirClient
from pyairctrl.http_client import HTTPAirClient
from pyairctrl.plain_coap_client import PlainCoAPAirClient


class CliBase:
    def __init__(self, client):
        self._client = client

    def _dump_keys(self, status, subset, printKey):
        for key in status:
            current_value = status[key]
            name_and_value = self._get_info_for_key(key, current_value, subset)
            if name_and_value is None:
                continue

            prefix = "[{key}]\t".format(key=key) if printKey else ""
            print(
                "{prefix}{name_and_value}".format(
                    prefix=prefix, name_and_value=name_and_value
                ).expandtabs(30)
            )

    def get_status(self, debug=False):
        status = self._client.get_status(debug)
        if status is None:
            print("No info found")
            return

        if debug:
            print("Raw status:")
            pprint.pprint(status)
        self._dump_keys(status, None, True)

    def set_values(self, values, debug=False):
        try:
            values = self._client.set_values(values)
        except urllib.error.HTTPError as e:
            print("Error setting values (response code: {})".format(e.code))

    def _get_info_for_key(self, key, current_value, subset):
        if key in STATUS_TRANSFORMER:
            info = STATUS_TRANSFORMER[key]
            if not subset is None and subset != info[1]:
                return None

            if not info[2] is None:
                current_value = info[2](current_value)
                if current_value is None:
                    return None
            return info[0].format(current_value)
        else:
            if not subset is None:
                return None

        return "{}: {}".format(key, current_value)

    def get_filters(self):
        status = self._client.get_filters()
        if status is None:
            print("No filter-info found")
            return

        self._dump_keys(status, "filter", False)

    def get_firmware(self):
        status = self._client.get_firmware()
        if status is None:
            print("No firmware-info found")
            return

        self._dump_keys(status, "firmware", False)


class CoAPCliBase(CliBase):
    def __init__(self, client):
        super().__init__(client)

    def get_wifi(self):
        print(
            "Getting wifi credentials is currently not supported when using CoAP. Use the app instead."
        )

    def set_wifi(self, ssid, pwd):
        print(
            "Setting wifi credentials is currently not supported when using CoAP. Use the app instead."
        )


class CoAPCli(CoAPCliBase):
    def __init__(self, host, port=5683, debug=False):
        super().__init__(CoAPAirClient(host, port, debug))


class PlainCoAPAirCli(CoAPCliBase):
    def __init__(self, host, port=5683):
        super().__init__(PlainCoAPAirClient(host, port))


class HTTPAirCli(CliBase):
    @staticmethod
    def ssdp(timeout=1, repeats=3, debug=False):
        response = HTTPAirClient.ssdp(timeout, repeats)
        if debug:
            pprint.pprint(response)
        return response

    def __init__(self, host, debug=True):
        super().__init__(HTTPAirClient(host, debug))

    def set_wifi(self, ssid, pwd):
        values = {}
        if ssid:
            values["ssid"] = ssid
        if pwd:
            values["password"] = pwd
        pprint.pprint(values)

        wifi = self._client.set_wifi(ssid, pwd)
        pprint.pprint(wifi)

    def get_wifi(self):
        wifi = self._client.get_wifi()
        self._dump_keys(wifi, None, False)

    def get_firmware(self):
        firmware = self._client.get_firmware()
        self._dump_keys(firmware, None, False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ipaddr", help="IP address of air purifier")
    parser.add_argument(
        "--protocol",
        help="set the communication protocol",
        choices=["http", "coap", "plain_coap"],
        default="http",
    )
    parser.add_argument("-d", "--debug", help="show debug output", action="store_true")
    parser.add_argument(
        "--om", help="set fan speed", choices=["1", "2", "3", "s", "t", "a"]
    )
    parser.add_argument("--pwr", help="power on/off", choices=["0", "1"])
    parser.add_argument(
        "--mode",
        help="set mode",
        choices=["P", "A", "AG", "F", "S", "M", "B", "N", "T", "GT"],
    )
    parser.add_argument(
        "--rhset", help="set target humidity", choices=["40", "50", "60", "70"]
    )
    parser.add_argument("--func", help="set function", choices=["P", "PH"])
    parser.add_argument(
        "--aqil", help="set light brightness", choices=["0", "25", "50", "75", "100"]
    )
    parser.add_argument("--uil", help="set button lights on/off", choices=["0", "1"])
    parser.add_argument(
        "--ddp",
        help="set indicator IAI/PM2.5/Gas/Humidity",
        choices=["0", "1", "2", "3"],
    )
    parser.add_argument(
        "--dt",
        help="set timer",
        choices=["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"],
    )
    parser.add_argument("--cl", help="set child lock", choices=["True", "False"])
    parser.add_argument("--wifi", help="read wifi options", action="store_true")
    parser.add_argument("--wifi-ssid", help="set wifi ssid")
    parser.add_argument("--wifi-pwd", help="set wifi password")
    parser.add_argument("--firmware", help="read firmware", action="store_true")
    parser.add_argument("--filters", help="read filters status", action="store_true")
    args = parser.parse_args()

    if args.ipaddr:
        devices = [{"ip": args.ipaddr}]
    else:
        if args.protocol in ["coap", "plain_coap"]:
            print(
                "Autodetection is not supported when using CoAP. Use --ipaddr to set an IP address."
            )
            sys.exit(1)

        devices = HTTPAirCli.ssdp(debug=args.debug)
        if not devices:
            print(
                "Air purifier not autodetected. Try --ipaddr option to force specific IP address."
            )
            sys.exit(1)

    for device in devices:
        if args.protocol == "http":
            c = HTTPAirCli(device["ip"])
        elif args.protocol == "plain_coap":
            c = PlainCoAPAirCli(device["ip"])
        elif args.protocol == "coap":
            c = CoAPCli(device["ip"], debug=args.debug)

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
            values["om"] = args.om
        if args.pwr:
            values["pwr"] = args.pwr
        if args.mode:
            values["mode"] = args.mode
        if args.rhset:
            values["rhset"] = int(args.rhset)
        if args.func:
            values["func"] = args.func
        if args.aqil:
            values["aqil"] = int(args.aqil)
        if args.ddp:
            values["ddp"] = args.ddp
        if args.uil:
            values["uil"] = args.uil
        if args.dt:
            values["dt"] = int(args.dt)
        if args.cl:
            values["cl"] = args.cl == "True"

        if values:
            c.set_values(values, debug=args.debug)
        else:
            c.get_status(debug=args.debug)


if __name__ == "__main__":
    main()
