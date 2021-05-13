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

    def get_status(self, subset=None):
        status = self._get()
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

    def get_firmware(self):
        status = self._get()
        # TODO Really transmit full status here?
        return status

    def get_filters(self):
        status = self._get()
        # TODO Really transmit full status here?
        return status

    def get_wifi(self):
        raise NotSupportedException

    def set_wifi(self, ssid, pwd):
        raise NotSupportedException