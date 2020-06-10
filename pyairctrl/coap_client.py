"""CoAP Air Client."""

# pylint: disable=invalid-name, missing-class-docstring, missing-function-docstring

import binascii
import hashlib
import json
import logging
import os
from abc import ABC, abstractmethod
from collections import OrderedDict

from coapthon import defines
from coapthon.client.helperclient import HelperClient
from Cryptodome.Cipher import AES
from Cryptodome.Util.Padding import pad, unpad


class WrongDigestException(Exception):
    pass


class NotSupportedException(Exception):
    pass


class HTTPAirClientBase(ABC):
    def __init__(self, host, port, debug=False):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel("WARN")
        self.server = host
        self.port = port
        self.debug = debug

    def get_status(self, debug=False):
        if debug:
            self.logger.setLevel("DEBUG")
        status = self._get()
        return status

    def set_values(self, values, debug=False):
        if debug:
            self.logger.setLevel("DEBUG")

        result = True
        for key in values:
            result = result and self._set(key, values[key])

        return result

    @abstractmethod
    def _get(self):
        pass

    @abstractmethod
    def _set(self, key, value):
        pass

    def get_firmware(self):
        status = self._get()
        return status

    def get_filters(self):
        status = self._get()
        return status

    def get_wifi(self):
        raise NotSupportedException

    def set_wifi(self, ssid, pwd):
        raise NotSupportedException


class CoAPAirClient(HTTPAirClientBase):
    SECRET_KEY = "JiangPan"

    def __init__(self, host, port=5683, debug=False):
        super().__init__(host, port, debug)
        self.client = self._create_coap_client(self.server, self.port)
        self._sync()

    def __del__(self):
        # TODO call a close method explicitly instead
        self.client.stop()

    def _create_coap_client(self, host, port):
        return HelperClient(server=(host, port))

    def _sync(self):
        self.syncrequest = binascii.hexlify(os.urandom(4)).decode("utf8").upper()
        self.client_key = self.client.post("/sys/dev/sync", self.syncrequest).payload

    def _decrypt_payload(self, encrypted_payload):
        encoded_counter = encrypted_payload[0:8]
        aes = self._handle_AES(encoded_counter)
        encoded_message = encrypted_payload[8:-64].upper()
        digest = encrypted_payload[-64:]
        calculated_digest = self._create_digest(encoded_counter, encoded_message)
        if digest != calculated_digest:
            raise WrongDigestException
        decoded_message = aes.decrypt(bytes.fromhex(encoded_message))
        unpaded_message = unpad(decoded_message, 16, style="pkcs7")
        return unpaded_message.decode("utf8")

    def _encrypt_payload(self, payload):
        self._update_client_key()
        aes = self._handle_AES(self.client_key)
        paded_message = pad(bytes(payload.encode("utf8")), 16, style="pkcs7")
        encoded_message = binascii.hexlify(aes.encrypt(paded_message)).decode("utf8").upper()
        digest = self._create_digest(self.client_key, encoded_message)
        return self.client_key + encoded_message + digest

    def _create_digest(self, id, encoded_message):
        digest = (
            hashlib.sha256(bytes((id + encoded_message).encode("utf8")))
            .hexdigest()
            .upper()
        )
        return digest

    def _update_client_key(self):
        self.client_key = "{:x}".format(int(self.client_key, 16) + 1).upper()

    def _handle_AES(self, id):
        key_and_iv = hashlib.md5((self.SECRET_KEY + id).encode()).hexdigest().upper()
        half_keylen = len(key_and_iv) // 2
        secret_key = key_and_iv[0:half_keylen]
        iv = key_and_iv[half_keylen:]
        return AES.new(
            bytes(secret_key.encode("utf8")), AES.MODE_CBC, bytes(iv.encode("utf8"))
        )

    def _get(self):
        path = "/sys/dev/status"
        decrypted_payload = None

        try:
            request = self.client.mk_request(defines.Codes.GET, path)
            request.observe = 0
            response = self.client.send_request(request, None, 2)
            encrypted_payload = response.payload
            decrypted_payload = self._decrypt_payload(encrypted_payload)
        except WrongDigestException:
            print("Message from device got corrupted")
        except Exception as e:
            print("Unexpected error:{}".format(e))

        if decrypted_payload is not None:
            return json.loads(decrypted_payload, object_pairs_hook=OrderedDict)[
                "state"
            ]["reported"]
        else:
            return {}

    def _set(self, key, value):
        path = "/sys/dev/control"
        try:
            payload = {
                "state": {
                    "desired": {
                        "CommandType": "app",
                        "DeviceId": "",
                        "EnduserId": "",
                        key: value,
                    }
                }
            }
            encrypted_payload = self._encrypt_payload(json.dumps(payload))
            response = self.client.post(path, encrypted_payload)
            if self.debug:
                print(response)
            return response.payload == '{"status":"success"}'
        except Exception as e:
            print("Unexpected error:{}".format(e))
