# pylint: disable=invalid-name, missing-class-docstring, missing-function-docstring

import base64
import json
import random
import os
import binascii
import flask
from Cryptodome.Cipher import AES
from Cryptodome.Util.Padding import pad, unpad


class HttpTestController:
    _sharedBase = int(
        "A4D1CBD5C3FD34126765A442EFB99905F8104DD258AC507FD6406CFF14266D31266FEA1E5C41564B777E690F5504F213160217B4B01B886A5E91547F9E2749F4D7FBD7D3B9A92EE1909D0D2263F80A76A6A24C087A091F531DBF0A0169B6A28AD662A4D18E73AFA32D779D5918D08BC8858F4DCEF97C2A24855E6EEB22B3B2E5",
        16,
    )

    _sharedPrime = int(
        "B10B8F96A080E01DDE92DE5EAE5D54EC52C99FBCFB06A3C69A6A9DCA52D23B616073E28675A23D189838EF1E2EE652C013ECB4AEA906112324975C3CD49B83BFACCBDD7D90C4BD7098488E9C219A73724EFFD6FAE5644738FAA31A4FF55BCCC0A151AF5F0DC8B4BD45BF37DF365C1A65E68CFDA76D4DA708DF1FB2BC2E4A4371",
        16,
    )

    _urlMapping = {
        "http://127.0.0.1/di/v1/products/0/wifi": "wifi",
        "http://127.0.0.1/di/v1/products/1/air": "status",
    }

    def __init__(self, device_key):
        self._override_dataset = None
        self._test_data = self._init_test_data()
        self._device_key = device_key

    def _init_test_data(self):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(dir_path, "data.json"), "r") as json_file:
            return json.load(json_file)

    def _encrypt(self, values, key):
        data = pad(bytearray(values, "ascii"), 16, style="pkcs7")
        iv = bytes(16)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        data_enc = cipher.encrypt(data)
        return data_enc

    def _aes_decrypt(self, data, key):
        iv = bytes(16)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        return cipher.decrypt(data)

    def _decrypt(self, data, key):
        payload = base64.b64decode(data)
        data = self._aes_decrypt(payload, key)
        # response starts with 2 random bytes, exclude them
        response = unpad(data, 16, style="pkcs7")[2:]
        return response.decode("ascii")

    def _padding_encrypt(self, values, key):
        # add two random bytes in front of the body
        data = "AA" + json.dumps(values)
        data = pad(bytearray(data, "ascii"), 16, style="pkcs7")
        iv = bytes(16)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        data_enc = cipher.encrypt(data)
        return base64.b64encode(data_enc)

    def security(self):
        b = random.getrandbits(256)
        B = pow(self._sharedBase, b, self._sharedPrime)

        dh = json.loads(flask.request.get_data().decode("ascii"))
        A = int(dh["diffie"], 16)
        s = pow(A, b, self._sharedPrime)
        s_bytes = s.to_bytes(128, byteorder="big")[:16]

        session_key_encrypted = self._encrypt(self._device_key, s_bytes)

        data = json.dumps(
            {
                "key": binascii.hexlify(session_key_encrypted).decode("utf8"),
                "hellman": format(B, "x"),
            }
        )
        data_enc = data.encode("ascii")

        return data_enc

    def get_status(self):
        return self._callback_get_data("status")

    def set_status(self):
        return self._callback_set_data('{"mode": "A"}')

    def get_wifi(self):
        return self._callback_get_data("wifi")

    def set_wifi(self):
        return self._callback_set_data('{"ssid": "1234", "password": "5678"}')

    def get_firmware(self):
        return self._callback_get_data("firmware")

    def get_filters(self):
        return self._callback_get_data("fltsts")

    def _callback_get_data(self, dataset):
        data = self._test_data["http"][dataset]["data"]
        json_data = json.loads(data)
        _encrypted_data = self._padding_encrypt(
            json_data, bytes(self._device_key.encode("ascii"))
        )
        return _encrypted_data

    def _callback_set_data(self, valid_data):
        _encrypted_data = flask.request.get_data()
        data = json.loads(
            self._decrypt(_encrypted_data, bytes(self._device_key.encode("ascii")))
        )

        if data != json.loads(valid_data):
            json_data = json.loads("{}")
        else:
            dataset = self._urlMapping[flask.request.url]
            status_data = self._test_data["http"][dataset]["data"]
            json_data = json.loads(status_data)

        _encrypted_data = self._padding_encrypt(
            json_data, bytes(self._device_key.encode("ascii"))
        )
        return _encrypted_data
