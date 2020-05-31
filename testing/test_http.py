# pylint: disable=invalid-name, missing-class-docstring, missing-function-docstring

from multiprocessing import Process
import os
import time
import json
import random
import base64
import flask
import pytest
import requests
from Cryptodome.Cipher import AES
from Cryptodome.Util.Padding import pad, unpad
from pyairctrl.http_client import HTTPAirClient
from pyairctrl.airctrl import HTTPAirCli

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


class TestHTTP:
    device_key = "1234567890123456"
    current_dataset = ""

    @pytest.fixture(scope="class")
    def air_client(self):
        return HTTPAirClient("127.0.0.1")

    @pytest.fixture(scope="class")
    def air_cli(self):
        return HTTPAirCli("127.0.0.1")

    @pytest.fixture(scope="class")
    def test_data(self):
        return self._test_data()

    def _test_data(self):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(dir_path, "data.json"), "r") as json_file:
            return json.load(json_file)

    @pytest.fixture(scope="class", autouse=True)
    def create_http_server(self):
        self.httpServer = HttpServer(5000)

        self.httpServer.add_url_rule(
            "/di/v1/products/0/security", view_func=self.security, methods=["PUT"]
        )
        self.httpServer.add_url_rule(
            "/di/v1/products/1/air", view_func=self.get_status, methods=["GET"]
        )
        self.httpServer.add_url_rule(
            "/di/v1/products/1/air", view_func=self.set_status, methods=["PUT"]
        )
        self.httpServer.add_url_rule(
            "/di/v1/products/0/wifi", view_func=self.get_wifi, methods=["GET"]
        )
        self.httpServer.add_url_rule(
            "/di/v1/products/0/wifi", view_func=self.set_wifi, methods=["PUT"]
        )
        self.httpServer.add_url_rule(
            "/di/v1/products/0/firmware", view_func=self.get_firmware, methods=["GET"]
        )
        self.httpServer.add_url_rule(
            "/di/v1/products/1/fltsts", view_func=self.get_filters, methods=["GET"]
        )
        self.httpServer.start()
        yield self.httpServer
        self.httpServer.stop()

    def test_get_valid_session_key(self, air_client):
        fpath = os.path.expanduser("~/../.pyairctrl")
        if os.path.isfile(fpath):
            os.remove(fpath)

        current_key = air_client.load_key()
        assert current_key.decode("ascii") == self.device_key

    def test_set_values(self, air_client):
        values = {}
        values["mode"] = "A"
        result = air_client.set_values(values)
        assert result == json.loads('{"status":"success"}')

    def test_set_wifi(self, air_client):
        result = air_client.set_wifi("1234", "5678")
        assert result == json.loads('{"status":"success"}')

    def test_get_status_is_valid(self, air_client, test_data):
        self.assert_json_data(air_client.get_status, "http-status", test_data)

    def test_get_wifi_is_valid(self, air_client, test_data):
        self.assert_json_data(air_client.get_wifi, "http-wifi", test_data)

    def test_get_firmware_is_valid(self, air_client, test_data):
        self.assert_json_data(air_client.get_firmware, "http-firmware", test_data)

    def test_get_filters_is_valid(self, air_client, test_data):
        self.assert_json_data(air_client.get_filters, "http-fltsts", test_data)

    def test_get_cli_status_is_valid(self, air_cli, test_data, capfd):
        self.assert_cli_data(air_cli.get_status, "http-status-cli", test_data, capfd)

    def test_get_cli_wifi_is_valid(self, air_cli, test_data, capfd):
        self.assert_cli_data(air_cli.get_wifi, "http-wifi-cli", test_data, capfd)

    def test_get_cli_firmware_is_valid(self, air_cli, test_data, capfd):
        self.assert_cli_data(
            air_cli.get_firmware, "http-firmware-cli", test_data, capfd
        )

    def test_get_cli_filters_is_valid(self, air_cli, test_data, capfd):
        self.assert_cli_data(air_cli.get_filters, "http-fltsts-cli", test_data, capfd)

    def assert_json_data(self, air_func, dataset, test_data):
        result = air_func()
        data = test_data[dataset]["data"]
        json_data = json.loads(data)
        assert result == json_data

    def assert_cli_data(self, air_func, dataset, test_data, capfd):
        air_func()
        result, err = capfd.readouterr()
        assert result == test_data[dataset]["data"]

    def security(self):
        b = random.getrandbits(256)
        B = pow(G, b, P)

        dh = json.loads(flask.request.get_data().decode("ascii"))
        A = int(dh["diffie"], 16)
        s = pow(A, b, P)
        s_bytes = s.to_bytes(128, byteorder="big")[:16]

        session_key_encrypted = encrypt(self.device_key, s_bytes)

        data = json.dumps(
            {"key": session_key_encrypted.hex(), "hellman": format(B, "x")}
        )
        data_enc = data.encode("ascii")

        return data_enc

    def get_status(self):
        return self.callback_get_data("http-status")

    def set_status(self):
        return self.callback_set_data('{"mode": "A"}')

    def get_wifi(self):
        return self.callback_get_data("http-wifi")

    def set_wifi(self):
        return self.callback_set_data('{"ssid": "1234", "password": "5678"}')

    def get_firmware(self):
        return self.callback_get_data("http-firmware")

    def get_filters(self):
        return self.callback_get_data("http-fltsts")

    def callback_get_data(self, dataset):
        data = self._test_data()[dataset]["data"]
        json_data = json.loads(data)
        encrypted_data = padding_encrypt(
            json_data, bytes(self.device_key.encode("ascii"))
        )
        return encrypted_data

    def callback_set_data(self, valid_data):
        encrypted_data = flask.request.get_data()
        data = json.loads(
            decrypt(encrypted_data, bytes(self.device_key.encode("ascii")))
        )

        success = "success" if data == json.loads(valid_data) else "failed"

        return padding_encrypt(
            json.loads('{{"status":"{}"}}'.format(success)),
            bytes(self.device_key.encode("ascii")),
        )
