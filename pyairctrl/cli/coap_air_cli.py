"""CoAP Air CLI."""

# pylint: disable=invalid-name, missing-class-docstring, missing-function-docstring

from ..client.coap_air_client import CoAPAirClient


class CoAPAirCli:
    def __init__(self, host, port=5683):
        self._client = CoAPAirClient(host, port)

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
            ddp_str = {"3": "Humidity", "1": "PM2.5", "0": "IAI"}
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
        status = self._client.get_values(debug)
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
