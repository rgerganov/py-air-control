"""v107 CLI."""

# pylint: disable=invalid-name, missing-class-docstring, missing-function-docstring

import pprint

from ..client.v_107_client import Version107Client

from .status_transformer import STATUS_TRANSFORMER


class Version107Cli:
    def __init__(self, host, port=5683, debug=False):
        self._client = Version107Client(host, port, debug)

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
