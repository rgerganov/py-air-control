#!/usr/bin/env python3

import argparse
import sys
import pprint

from pyairctrl.status_transformer import STATUS_TRANSFORMER
from pyairctrl.coap_client import CoAPAirClient
from pyairctrl.http_client import HTTPAirClient
from pyairctrl.plain_coap_client import PlainCoAPAirClient


class CoAPCli:
    def __init__(self, host, port=5683, debug=False):
        self._client = CoAPAirClient(host, port, debug)

    def _get_info_for_key(self, key, current_value):
        if key in STATUS_TRANSFORMER:
            info = STATUS_TRANSFORMER[key]
            if not info[1] is None:
                current_value = info[1](current_value)
                if current_value is None:
                    return None
            return info[0].format(current_value)

        return "{}: {}".format(key, current_value)

    def _dump_status(self, status, debug=False):
        if debug:
            print("Raw status:")
            pprint.pprint(status)
        for key in status:
            current_value = status[key]
            name_and_value = self._get_info_for_key(key, current_value)
            if name_and_value is None:
                continue

            print(
                "[{key}]\t{name_and_value}".format(
                    key=key, name_and_value=name_and_value
                ).expandtabs(30)
            )

    def get_status(self, debug=False):
        status = self._client.get_status(debug)
        if status is not None:
            return self._dump_status(status, debug=debug)

    def set_values(self, values, debug=False):
        self._client.set_values(values, debug)

    def get_firmware(self):
        status = self._client.get_firmware()
        if status is None:
            print("No version-info found")
            return

        print(
            self._get_info_for_key(
                "swversion", status["swversion"] if "swversion" in status else "nA"
            )
        )
        print(self._get_info_for_key("ota", status["ota"] if "ota" in status else "nA"))

    def get_filters(self):
        status = self._client.get_filters()
        if status is None:
            print("No version-info found")
            return

        if "fltsts0" in status:
            print(self._get_info_for_key("fltsts0", status["fltsts0"]))
        if "fltsts1" in status:
            print(self._get_info_for_key("fltsts1", status["fltsts1"]))
        if "fltsts2" in status:
            print(self._get_info_for_key("fltsts2", status["fltsts2"]))
        if "wicksts" in status:
            print(self._get_info_for_key("wicksts", status["wicksts"]))

    def get_wifi(self):
        print(
            "Getting wifi credentials is currently not supported when using CoAP. Use the app instead."
        )

    def set_wifi(self, ssid, pwd):
        print(
            "Setting wifi credentials is currently not supported when using CoAP. Use the app instead."
        )


class HTTPAirCli:
    @staticmethod
    def ssdp(timeout=1, repeats=3, debug=False):
        response = HTTPAirClient.ssdp(timeout, repeats)
        if debug:
            pprint.pprint(response)
        return response

    def __init__(self, host, debug=True):
        self._client = HTTPAirClient(host, debug)

    def set_values(self, values, debug=False):
        try:
            values = self._client.set_values(values)
            self._dump_status(values, debug=debug)
        except urllib.error.HTTPError as e:
            print("Error setting values (response code: {})".format(e.code))

    def set_wifi(self, ssid, pwd):
        values = {}
        if ssid:
            values["ssid"] = ssid
        if pwd:
            values["password"] = pwd
        pprint.pprint(values)

        wifi = self._client.set_wifi(ssid, pwd)
        pprint.pprint(wifi)

    def _dump_status(self, status, debug=False):
        if debug:
            pprint.pprint(status)
            print()

        if "pwr" in status:
            pwr = status["pwr"]
            pwr_str = {"1": "ON", "0": "OFF"}
            pwr = pwr_str.get(pwr, pwr)
            print("[pwr]   Power: {}".format(pwr))
        if "pm25" in status:
            pm25 = status["pm25"]
            print("[pm25]  PM25: {}".format(pm25))
        if "rh" in status:
            rh = status["rh"]
            print("[rh]    Humidity: {}".format(rh))
        if "rhset" in status:
            rhset = status["rhset"]
            print("[rhset] Target humidity: {}".format(rhset))
        if "iaql" in status:
            iaql = status["iaql"]
            print("[iaql]  Allergen index: {}".format(iaql))
        if "temp" in status:
            temp = status["temp"]
            print("[temp]  Temperature: {}".format(temp))
        if "func" in status:
            func = status["func"]
            func_str = {"P": "Purification", "PH": "Purification & Humidification"}
            func = func_str.get(func, func)
            print("[func]  Function: {}".format(func))
        if "mode" in status:
            mode = status["mode"]
            mode_str = {
                "P": "auto",
                "A": "allergen",
                "S": "sleep",
                "M": "manual",
                "B": "bacteria",
                "N": "night",
                "T": "turbo",
            }
            mode = mode_str.get(mode, mode)
            print("[mode]  Mode: {}".format(mode))
        if "om" in status:
            om = status["om"]
            om_str = {"s": "silent", "t": "turbo"}
            om = om_str.get(om, om)
            print("[om]    Fan speed: {}".format(om))
        if "aqil" in status:
            aqil = status["aqil"]
            print("[aqil]  Light brightness: {}".format(aqil))
        if "uil" in status:
            uil = status["uil"]
            uil_str = {"1": "ON", "0": "OFF"}
            uil = uil_str.get(uil, uil)
            print("[uil]   Buttons light: {}".format(uil))
        if "ddp" in status:
            ddp = status["ddp"]
            ddp_str = {"1": "PM2.5", "0": "IAI", "2": "Gas"}
            ddp = ddp_str.get(ddp, ddp)
            print("[ddp]   Used index: {}".format(ddp))
        if "wl" in status:
            wl = status["wl"]
            print("[wl]    Water level: {}".format(wl))
        if "cl" in status:
            cl = status["cl"]
            print("[cl]    Child lock: {}".format(cl))
        if "dt" in status:
            dt = status["dt"]
            if dt != 0:
                print("[dt]    Timer: {} hours".format(dt))
        if "dtrs" in status:
            dtrs = status["dtrs"]
            if dtrs != 0:
                print("[dtrs]  Timer: {} minutes left".format(dtrs))
        if "err" in status:
            err = status["err"]
            if err != 0:
                err_str = {
                    49408: "no water",
                    32768: "water tank open",
                    49155: "pre-filter must be cleaned",
                }
                err = err_str.get(err, err)
                print("-" * 20)
                print("Error: {}".format(err))

    def get_status(self, debug=False):
        status = self._client.get_status()
        self._dump_status(status, debug=debug)

    def get_wifi(self):
        wifi = self._client.get_wifi()
        pprint.pprint(wifi)

    def get_firmware(self):
        firmware = self._client.get_firmware()
        pprint.pprint(firmware)

    def get_filters(self):
        filters = self._client.get_filters()
        print("Pre-filter and Wick: clean in {} hours".format(filters["fltsts0"]))
        if "wicksts" in filters:
            print("Wick filter: replace in {} hours".format(filters["wicksts"]))
        print("Active carbon filter: replace in {} hours".format(filters["fltsts2"]))
        print("HEPA filter: replace in {} hours".format(filters["fltsts1"]))


class PlainCoAPAirCli:
    def __init__(self, host, port=5683):
        self._client = PlainCoAPAirClient(host, port)

    def _dump_status(self, status, debug=False):
        if debug:
            print("Raw status: " + str(status))
        if "name" in status:
            name = status["name"]
            print("[name]        Name: {}".format(name))
        if "modelid" in status:
            modelid = status["modelid"]
            print("[modelid]     ModelId: {}".format(modelid))
        if "swversion" in status:
            swversion = status["swversion"]
            print("[swversion]   Version: {}".format(swversion))
        if "StatusType" in status:
            statustype = status["StatusType"]
            print("[StatusType]  StatusType: {}".format(statustype))
        if "ota" in status:
            ota = status["ota"]
            print("[ota]         Over the air updates: {}".format(ota))
        if "Runtime" in status:
            runtime = status["Runtime"]
            print(
                "[Runtime]     Runtime: {} hours".format(
                    round(((runtime / (1000 * 60 * 60)) % 24), 2)
                )
            )
        if "pwr" in status:
            pwr = status["pwr"]
            pwr_str = {"1": "ON", "0": "OFF"}
            pwr = pwr_str.get(pwr, pwr)
            print("[pwr]         Power: {}".format(pwr))
        if "pm25" in status:
            pm25 = status["pm25"]
            print("[pm25]        PM25: {}".format(pm25))
        if "rh" in status:
            rh = status["rh"]
            print("[rh]          Humidity: {}".format(rh))
        if "rhset" in status:
            rhset = status["rhset"]
            print("[rhset]       Target humidity: {}".format(rhset))
        if "iaql" in status:
            iaql = status["iaql"]
            print("[iaql]        Allergen index: {}".format(iaql))
        if "temp" in status:
            temp = status["temp"]
            print("[temp]        Temperature: {}".format(temp))
        if "func" in status:
            func = status["func"]
            func_str = {"P": "Purification", "PH": "Purification & Humidification"}
            func = func_str.get(func, func)
            print("[func]        Function: {}".format(func))
        if "mode" in status:
            mode = status["mode"]
            mode_str = {
                "P": "auto",
                "A": "allergen",
                "S": "sleep",
                "M": "manual",
                "B": "bacteria",
                "N": "night",
                "T": "turbo",
            }
            mode = mode_str.get(mode, mode)
            print("[mode]        Mode: {}".format(mode))
        if "om" in status:
            om = status["om"]
            om_str = {"s": "silent", "t": "turbo"}
            om = om_str.get(om, om)
            print("[om]          Fan speed: {}".format(om))
        if "aqil" in status:
            aqil = status["aqil"]
            print("[aqil]        Light brightness: {}".format(aqil))
        if "uil" in status:
            uil = status["uil"]
            uil_str = {"1": "ON", "0": "OFF"}
            uil = uil_str.get(uil, uil)
            print("[uil]         Buttons light: {}".format(uil))
        if "ddp" in status:
            ddp = status["ddp"]
            ddp_str = {"3": "Humidity", "1": "PM2.5", "2": "Gas", "0": "IAI"}
            ddp = ddp_str.get(ddp, ddp)
            print("[ddp]         Used index: {}".format(ddp))
        if "wl" in status:
            wl = status["wl"]
            print("[wl]          Water level: {}".format(wl))
        if "cl" in status:
            cl = status["cl"]
            print("[cl]          Child lock: {}".format(cl))
        if "dt" in status:
            dt = status["dt"]
            if dt != 0:
                print("[dt]          Timer: {} hours".format(dt))
        if "dtrs" in status:
            dtrs = status["dtrs"]
            if dtrs != 0:
                print("[dtrs]        Timer: {} minutes left".format(dtrs))
        if "fltsts0" in status:
            fltsts0 = status["fltsts0"]
            print(
                "[fltsts0]     Pre-filter and Wick: clean in {} hours".format(fltsts0)
            )
        if "fltsts1" in status:
            fltsts1 = status["fltsts1"]
            print("[fltsts1]     HEPA filter: replace in {} hours".format(fltsts1))
        if "fltsts2" in status:
            fltsts2 = status["fltsts2"]
            print(
                "[fltsts2]     Active carbon filter: replace in {} hours".format(
                    fltsts2
                )
            )
        if "wicksts" in status:
            wicksts = status["wicksts"]
            print("[wicksts]     Wick filter: replace in {} hours".format(wicksts))
        if "err" in status:
            err = status["err"]
            if err != 0:
                err_str = {
                    49408: "no water",
                    32768: "water tank open",
                    49155: "pre-filter must be cleaned",
                }
                err = err_str.get(err, err)
                print("-" * 20)
                print("[ERROR] Message: {}".format(err))

    def set_values(self, values, debug=False):
        self._client.set_values(values, debug)

    def get_status(self, debug=False):
        status = self._client.get_status(debug)
        return self._dump_status(status, debug=debug)

    def get_wifi(self):
        print(
            "Getting wifi credentials is currently not supported when using CoAP. Use the app instead."
        )

    def set_wifi(self, ssid, pwd):
        print(
            "Setting wifi credentials is currently not supported when using CoAP. Use the app instead."
        )

    def get_firmware(self):
        status = self._client.get_firmware()
        print("Software version: {}".format(status["swversion"]))
        print("Over the air updates: {}".format(status["ota"]))

    def get_filters(self):
        status = self._client.get_filters()
        print("Pre-filter and Wick: clean in {} hours".format(status["fltsts0"]))
        print("HEPA filter: replace in {} hours".format(status["fltsts1"]))
        print("Active carbon filter: replace in {} hours".format(status["fltsts2"]))
        print("Wick filter: replace in {} hours".format(status["wicksts"]))


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
    parser.add_argument("--om", help="set fan speed", choices=["1", "2", "3", "s", "t", "a"])
    parser.add_argument("--pwr", help="power on/off", choices=["0", "1"])
    parser.add_argument(
        "--mode", help="set mode", choices=["P", "A", "S", "M", "B", "N", "T"]
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
        "--ddp", help="set indicator IAI/PM2.5/Gas/Humidity", choices=["0", "1", "2", "3"]
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
