"""CoAP Air Client."""

# pylint: disable=invalid-name, missing-class-docstring, missing-function-docstring

import binascii
import hashlib
import os

from Cryptodome.Cipher import AES
from Cryptodome.Util.Padding import pad, unpad
from .base_client import CoAPAirClientBase


class WrongDigestException(Exception):
    pass


class CoAPAirClient(CoAPAirClientBase):
    SECRET_KEY = "JiangPan"

    def __init__(self, host, port=5683, debug=False):
        super().__init__(host, port, debug)

    def _initConnection(self):
        self.syncrequest = binascii.hexlify(os.urandom(4)).decode("utf8").upper()
        resp = self.client.post(self.SYNC_PATH, self.syncrequest, timeout=5)
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
