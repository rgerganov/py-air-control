import json
import logging
from abc import ABC, abstractmethod
from collections import OrderedDict

from coapthon import defines
from coapthon.client.helperclient import HelperClient
from coapthon.messages.request import Request

from pyairctrl.status_transformer import STATUS_TRANSFORMER


class NotSupportedException(Exception):
    pass


class AirClientBase(ABC):
    def __init__(self, host, debug=False):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel("WARN") if debug else self.logger.setLevel("DEBUG")
        self._host = host
        self._debug = debug

    def _get_info_for_key(self, key, raw_value, subset):
        current_value = raw_value
        subsets = None
        name = None
        rawDescription = None
        valueDescription = None

        if key in STATUS_TRANSFORMER:
            instructions = STATUS_TRANSFORMER[key]
            name = instructions["fieldname"]
            subsets = instructions["subsets"]
            rawDescription = instructions["rawDescription"]
            valueDescription = instructions["transformDescription"]

            if not subset is None and subset not in subsets:
                return None

            if not instructions["transform"] is None:
                current_value = instructions["transform"](raw_value)
        else:
            if not subset is None:
                return None

        return {
            "name": name,
            "raw": raw_value,
            "value": current_value,
            "subsets": subsets,
            "rawDescription": rawDescription,
            "valueDescription": valueDescription,
        }

    def _dump_keys(self, status, subset):
        new_status = status.copy()
        for key in status:
            current_value = status[key]
            name_and_value = self._get_info_for_key(key, current_value, subset)
            if name_and_value is None:
                new_status.pop(key, None)
                continue

            new_status[key] = name_and_value
        return new_status

    @abstractmethod
    def get_information(self, subset=None):
        pass


class CoAPAirClientBase(AirClientBase):
    STATUS_PATH = "/sys/dev/status"
    CONTROL_PATH = "/sys/dev/control"
    SYNC_PATH = "/sys/dev/sync"

    def __init__(self, host, port, debug=False):
        super().__init__(host, debug)
        self.port = port
        self.client = self._create_coap_client(self._host, self.port)
        self.response = None
        self._initConnection()

    def __del__(self):
        if self.response:
            self.client.cancel_observing(self.response, True)
        self.client.stop()

    def _create_coap_client(self, host, port):
        return HelperClient(server=(host, port))

    def get_information(self, subset=None):
        if subset == "wifi":
            raise NotSupportedException(
                "Getting wifi credentials is currently not supported when using CoAP. Use the app instead."
            )

        status = self._get()
        status = self._dump_keys(status, subset)
        return status

    def set_values(self, values):
        result = True
        for key in values:
            result = result and self._set(key, values[key])

        return result

    def _get(self):
        payload = None

        try:
            request = self.client.mk_request(defines.Codes.GET, self.STATUS_PATH)
            request.observe = 0
            self.response = self.client.send_request(request, None, 2)
            if self.response:
                payload = self._transform_payload_after_receiving(self.response.payload)
        except Exception as e:
            print("Unexpected error:{}".format(e))

        if payload:
            try:
                return json.loads(payload, object_pairs_hook=OrderedDict)["state"][
                    "reported"
                ]
            except json.decoder.JSONDecodeError:
                print("JSONDecodeError, you may have choosen the wrong coap protocol!")

        return {}

    def _set(self, key, payload):
        try:
            payload = self._transform_payload_before_sending(json.dumps(payload))
            response = self.client.post(self.CONTROL_PATH, payload)

            if self._debug:
                print(response)
            return response.payload == '{"status":"success"}'
        except Exception as e:
            print("Unexpected error:{}".format(e))

    def _send_empty_message(self):
        request = Request()
        request.destination = server = (self._host, self.port)
        request.code = defines.Codes.EMPTY.number
        self.client.send_empty(request)

    @abstractmethod
    def _initConnection(self):
        pass

    @abstractmethod
    def _transform_payload_after_receiving(self, payload):
        pass

    @abstractmethod
    def _transform_payload_before_sending(self, payload):
        pass

    def set_wifi(self, ssid, pwd):
        raise NotSupportedException