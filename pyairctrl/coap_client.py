"""CoAP Air Client."""

# pylint: disable=invalid-name, missing-class-docstring, missing-function-docstring

import binascii
import hashlib
import json
import logging
import os
from abc import ABC, abstractmethod
from collections import OrderedDict

from pyairctrl import aiocoap_monkeypatch
from aiocoap import (
    Context,
    GET,
    Message,
    NON,
    POST,
)
from Cryptodome.Cipher import AES
from Cryptodome.Util.Padding import pad, unpad


class WrongDigestException(Exception):
    pass


class NotSupportedException(Exception):
    pass


class CoAPAirClientBase(ABC):
    STATUS_PATH = "/sys/dev/status"
    CONTROL_PATH = "/sys/dev/control"
    SYNC_PATH = "/sys/dev/sync"

    def __init__(self, host, port, debug=False):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel("WARN")
        self.server = host
        self.port = port
        self.debug = debug
        self.client = None

    @classmethod
    async def create(cls, *args, **kwargs):
        obj = cls(*args, **kwargs)
        await obj._init()
        return obj

    async def _init(self):
        self.client = await Context.create_client_context()
        await self._initConnection()

    async def shutdown(self) -> None:
        if self.client:
            await self.client.shutdown()

    async def get_status(self, debug=False):
        if debug:
            self.logger.setLevel("DEBUG")
        status = await self._get()
        return status

    def set_values(self, values, debug=False):
        if debug:
            self.logger.setLevel("DEBUG")

        result = True
        for key in values:
            result = result and self._set(key, values[key])

        return result

    async def _get(self):
        payload = None

        try:
            request = Message(
                code=GET,
                mtype=NON,
                uri=f"coap://{self.server}:{self.port}{self.STATUS_PATH}",
            )
            request.opt.observe = 0
            response = await self.client.request(request).response
            if response:
                payload = self._transform_payload_after_receiving(
                    response.payload.decode()
                )
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

            if self.debug:
                print(response)
            return response.payload == '{"status":"success"}'
        except Exception as e:
            print("Unexpected error:{}".format(e))

    def _send_empty_message(self):
        request = Request()
        request.destination = server = (self.server, self.port)
        request.code = defines.Codes.EMPTY.number
        self.client.send_empty(request)

    @abstractmethod
    async def _initConnection(self):
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


class CoAPAirClient(CoAPAirClientBase):
    SECRET_KEY = "JiangPan"

    def __init__(self, host, port=5683, debug=False):
        super().__init__(host, port, debug)

    async def _initConnection(self):
        syncrequest = os.urandom(4).hex().upper()
        request = Message(
            code=POST,
            mtype=NON,
            uri=f"coap://{self.server}:{self.port}{self.SYNC_PATH}",
            payload=syncrequest.encode(),
        )
        resp = await self.client.request(request).response
        if resp:
            self.client_key = resp.payload
        else:
            self.client.stop()
            raise Exception("sync timeout")

    def _transform_payload_after_receiving(self, encrypted_payload):
        try:
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
        except WrongDigestException:
            print("Message from device got corrupted")

    def _transform_payload_before_sending(self, payload):
        self._update_client_key()
        aes = self._handle_AES(self.client_key)
        paded_message = pad(bytes(payload.encode("utf8")), 16, style="pkcs7")
        encoded_message = (
            binascii.hexlify(aes.encrypt(paded_message)).decode("utf8").upper()
        )
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

    def _set(self, key, value):
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
        return super()._set(key, payload)
