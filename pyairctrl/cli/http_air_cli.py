"""HTTP Air CLI."""

# pylint: disable=invalid-name, missing-class-docstring, missing-function-docstring

import pprint
import urllib.request

from ..client.http_air_client import HTTPAirClient


class HTTPAirCli:
    @staticmethod
    def ssdp(timeout=1, repeats=3, debug=False):
        response = HTTPAirClient.ssdp(timeout, repeats)
        if debug:
            pprint.pprint(response)
        return response

    def __init__(self, host):
        self._client = HTTPAirClient(host)

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

    def load_key(self):
        self._client.load_key()

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
            ddp_str = {"1": "PM2.5", "0": "IAI"}
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
