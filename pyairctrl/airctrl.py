#!/usr/bin/env python3

import argparse
import sys
import pprint
import json

from pyairctrl.base_client import (
    NotSupportedException,
    SetValueException,
    AirClientBase,
)
from pyairctrl.coap_client import CoAPAirClient
from pyairctrl.http_client import HTTPAirClient
from pyairctrl.plain_coap_client import PlainCoAPAirClient
from pyairctrl.cli_format import CLI_FORMAT


class ClientFactory:
    def __init__(self, client, debug):
        self._client: AirClientBase = client
        self._debug = debug

    @staticmethod
    def _format_key_values(status):
        for key in status:
            if status[key]["value"] is None:
                continue

            name_and_value = ClientFactory._get_name_for_key(key, status[key])

            prefix = "[{key}]\t".format(key=key)
            print(
                "{prefix}{name_and_value}".format(
                    prefix=prefix, name_and_value=name_and_value
                ).expandtabs(30)
            )

    @staticmethod
    def _get_name_for_key(key, singleEntry):
        formatter = (
            CLI_FORMAT[key]["format"]
            if key in CLI_FORMAT
            else "{name}: {{}}".format(name=singleEntry["name"])
            if not singleEntry["name"] is None
            else "{name}: {{}}".format(name=key)
        )
        return formatter.format(singleEntry["value"])

    def get_information(self, subset=None):
        try:
            status = self._client.get_information(subset)
            if status is None:
                noneInfo = (
                    "info" if subset is None else "{subset}-info".format(subset=subset)
                )
                print("No {noneInfo} found".format(noneInfo=noneInfo))
                return

            if self._debug:
                print("Raw status:")
                print(json.dumps(status, indent=4))
            self._format_key_values(status)
        except NotSupportedException as e:
            print(e)

    def set_values(self, subset, values):
        try:
            if self._debug:
                pprint.pprint(values)
            values = self._client.set_values(subset, values)
        except (NotSupportedException, SetValueException) as e:
            print(e)

    @classmethod
    def get_devices(cls, protocol, ipaddr, debug):
        if ipaddr:
            return [{"ip": ipaddr}]

        try:
            client = cls.get_client_class(protocol)
            devices = client.get_devices(debug)
            if debug:
                pprint.pprint(devices)
            if not devices:
                print(
                    "Air purifier not autodetected. Try --ipaddr option to force specific IP address."
                )
                sys.exit(1)
            return devices
        except NotSupportedException as e:
            print(e)
            sys.exit(1)

    @classmethod
    def get_client_class(cls, protocol):
        if protocol == "http":
            return HTTPAirClient
        elif protocol == "plain_coap":
            return PlainCoAPAirClient
        elif protocol == "coap":
            return CoAPAirClient

    @classmethod
    def create(cls, protocol, host, debug):
        client = cls.get_client_class(protocol)
        return cls(client(host, debug=debug), debug)


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

    devices = ClientFactory.get_devices(args.protocol, args.ipaddr, debug=args.debug)
    for device in devices:
        c = ClientFactory.create(args.protocol, device["ip"], debug=args.debug)

        subset = None
        if args.wifi or args.wifi_ssid or args.wifi_pwd:
            subset = "wifi"
        if args.firmware:
            subset = "firmware"
        if args.filters:
            subset = "filter"

        values = {}
        if args.wifi_ssid:
            values["ssid"] = args.wifi_ssid
        if args.wifi_pwd:
            values["password"] = args.wifi_pwd

        if subset is None:
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
            c.set_values(subset, values)

        c.get_information(subset)


if __name__ == "__main__":
    main()
