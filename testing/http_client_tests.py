# pylint: disable=invalid-name, missing-class-docstring, missing-function-docstring

import unittest
from multiprocessing import Process
import os
import time
import json
import random
import base64
import flask
import requests
from Cryptodome.Cipher import AES
from Cryptodome.Util.Padding import pad, unpad
from pyairctrl.http_client import HTTPAirClient

G = int(
    "A4D1CBD5C3FD34126765A442EFB99905F8104DD258AC507FD6406CFF14266D31266FEA1E5C41564B777E690F5504F213160217B4B01B886A5E91547F9E2749F4D7FBD7D3B9A92EE1909D0D2263F80A76A6A24C087A091F531DBF0A0169B6A28AD662A4D18E73AFA32D779D5918D08BC8858F4DCEF97C2A24855E6EEB22B3B2E5",
    16,
)

P = int(
    "B10B8F96A080E01DDE92DE5EAE5D54EC52C99FBCFB06A3C69A6A9DCA52D23B616073E28675A23D189838EF1E2EE652C013ECB4AEA906112324975C3CD49B83BFACCBDD7D90C4BD7098488E9C219A73724EFFD6FAE5644738FAA31A4FF55BCCC0A151AF5F0DC8B4BD45BF37DF365C1A65E68CFDA76D4DA708DF1FB2BC2E4A4371",
    16,
)


def encrypt(values, key):
    data = pad(bytearray(values, "ascii"), 16, style="pkcs7")
    iv = bytes(16)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    data_enc = cipher.encrypt(data)
    return data_enc


def aes_decrypt(data, key):
    iv = bytes(16)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return cipher.decrypt(data)


def decrypt(data, key):
    payload = base64.b64decode(data)
    data = aes_decrypt(payload, key)
    # response starts with 2 random bytes, exclude them
    response = unpad(data, 16, style="pkcs7")[2:]
    return response.decode("ascii")


def padding_encrypt(values, key):
    # add two random bytes in front of the body
    data = "AA" + json.dumps(values)
    data = pad(bytearray(data, "ascii"), 16, style="pkcs7")
    iv = bytes(16)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    data_enc = cipher.encrypt(data)
    return base64.b64encode(data_enc)


class HttpServer:
    def __init__(self, port):
        super().__init__()
        self.flask_server = flask.Flask(__name__)
        self.port = port
        self.process = Process(target=self._run)
        os.environ["FLASK_ENV"] = "development"

    def _test_connection(self):
        index_url = "http://127.0.0.1:{}".format(self.port)
        try:
            requests.get(url=index_url)
            return True
        except requests.exceptions.ConnectionError:
            return False

    def _run(self):
        self.flask_server.run(port=self.port, debug=False)

    def start(self):
        self.process.start()
        while not self._test_connection():
            time.sleep(1)

    def stop(self):
        self.process.terminate()
        self.process.join()

    def add_url_rule(self, rule, view_func, methods):
        self.flask_server.add_url_rule(rule, view_func=view_func, methods=methods)


class HTTPClientTests(unittest.TestCase):
    device_key = "1234567890123456"
    current_dataset = ""

    @classmethod
    def setUpClass(cls):
        cls.httpServer = HttpServer(80)
        dir_path = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(dir_path, "data.json"), "r") as json_file:
            cls.test_data = json.load(json_file)
        cls.httpServer.add_url_rule(
            "/di/v1/products/0/security", view_func=cls.security, methods=["PUT"]
        )
        cls.httpServer.add_url_rule(
            "/di/v1/products/1/air", view_func=cls.get_status, methods=["GET"]
        )
        cls.httpServer.add_url_rule(
            "/di/v1/products/1/air", view_func=cls.set_status, methods=["PUT"]
        )
        cls.httpServer.add_url_rule(
            "/di/v1/products/0/wifi", view_func=cls.get_wifi, methods=["GET"]
        )
        cls.httpServer.add_url_rule(
            "/di/v1/products/0/wifi", view_func=cls.set_wifi, methods=["PUT"]
        )
        cls.httpServer.add_url_rule(
            "/di/v1/products/0/firmware", view_func=cls.get_firmware, methods=["GET"]
        )
        cls.httpServer.add_url_rule(
            "/di/v1/products/1/fltsts", view_func=cls.get_filters, methods=["GET"]
        )
        cls.httpServer.start()
        cls.airClient = HTTPAirClient("127.0.0.1")

    @classmethod
    def tearDownClass(cls):
        cls.httpServer.stop()

    def test_ssdp(self):
        # missing
        pass

    def test_get_valid_session_key(self):
        fpath = os.path.expanduser("~/../.pyairctrl")
        if os.path.isfile(fpath):
            os.remove(fpath)

        current_key = self.airClient.load_key()
        self.assertEqual(current_key.decode("ascii"), self.device_key)

    def test_set_values(self):
        values = {}
        values["mode"] = "A"
        result = self.airClient.set_values(values)
        self.assertEqual(result, json.loads('{"sucess":"true"}'))

    def test_set_wifi(self):
        result = self.airClient.set_wifi("1234", "5678")
        self.assertEqual(result, json.loads('{"sucess":"true"}'))

    def test_get_status_is_valid(self):
        self.assert_json_data(self.airClient.get_status, "AC2729-status")

    def test_get_wifi_is_valid(self):
        self.assert_json_data(self.airClient.get_wifi, "AC2729-wifi")

    def test_get_firmware_is_valid(self):
        self.assert_json_data(self.airClient.get_firmware, "AC2729-firmware")

    def test_get_filters_is_valid(self):
        self.assert_json_data(self.airClient.get_filters, "AC2729-fltsts")

    def test_pair(self):
        # missing
        pass

    def assert_json_data(self, air_func, dataset):
        result = air_func()
        data = self.test_data[dataset]["data"]
        json_data = json.loads(data)
        self.assertEqual(result, json_data)

    @classmethod
    def security(cls):
        b = random.getrandbits(256)
        B = pow(G, b, P)

        dh = json.loads(flask.request.get_data().decode("ascii"))
        A = int(dh["diffie"], 16)
        s = pow(A, b, P)
        s_bytes = s.to_bytes(128, byteorder="big")[:16]

        session_key_encrypted = encrypt(cls.device_key, s_bytes)

        data = json.dumps(
            {"key": session_key_encrypted.hex(), "hellman": format(B, "x")}
        )
        data_enc = data.encode("ascii")

        return data_enc

    @classmethod
    def get_status(cls):
        return cls.callback_get_data("AC2729-status")

    @classmethod
    def set_status(cls):
        return cls.callback_set_data('{"mode": "A"}')

    @classmethod
    def get_wifi(cls):
        return cls.callback_get_data("AC2729-wifi")

    @classmethod
    def set_wifi(cls):
        return cls.callback_set_data('{"ssid": "1234", "password": "5678"}')

    @classmethod
    def get_firmware(cls):
        return cls.callback_get_data("AC2729-firmware")

    @classmethod
    def get_filters(cls):
        return cls.callback_get_data("AC2729-fltsts")

    @classmethod
    def callback_get_data(cls, dataset):
        data = cls.test_data[dataset]["data"]
        json_data = json.loads(data)
        encrypted_data = padding_encrypt(
            json_data, bytes(cls.device_key.encode("ascii"))
        )
        return encrypted_data

    @classmethod
    def callback_set_data(cls, valid_data):
        encrypted_data = flask.request.get_data()
        data = json.loads(
            decrypt(encrypted_data, bytes(cls.device_key.encode("ascii")))
        )

        success = str(data == json.loads(valid_data)).lower()

        return padding_encrypt(
            json.loads('{{"sucess":"{}"}}'.format(success)),
            bytes(cls.device_key.encode("ascii")),
        )


if __name__ == "__main__":
    unittest.main()
