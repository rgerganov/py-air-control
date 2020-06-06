# pylint: disable=invalid-name, missing-class-docstring, missing-function-docstring

import os
import json
import pytest
from pyairctrl.http_client import HTTPAirClient
from pyairctrl.airctrl import HTTPAirCli
from http_test_server import HttpTestServer
from http_test_controller import HttpTestController


class TestHTTP:
    device_key = "1234567890123456"

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

    @pytest.fixture(scope="class")
    def controller(self):
        return HttpTestController(self.device_key)

    @pytest.fixture(scope="class", autouse=True)
    def create_http_server(self, controller):
        self.httpServer = HttpTestServer(5000)

        self.httpServer.add_url_rule(
            "/di/v1/products/0/security", view_func=controller.security, methods=["PUT"]
        )
        self.httpServer.add_url_rule(
            "/di/v1/products/1/air", view_func=controller.get_status, methods=["GET"]
        )
        self.httpServer.add_url_rule(
            "/di/v1/products/1/air", view_func=controller.set_status, methods=["PUT"]
        )
        self.httpServer.add_url_rule(
            "/di/v1/products/0/wifi", view_func=controller.get_wifi, methods=["GET"]
        )
        self.httpServer.add_url_rule(
            "/di/v1/products/0/wifi", view_func=controller.set_wifi, methods=["PUT"]
        )
        self.httpServer.add_url_rule(
            "/di/v1/products/0/firmware",
            view_func=controller.get_firmware,
            methods=["GET"],
        )
        self.httpServer.add_url_rule(
            "/di/v1/products/1/fltsts",
            view_func=controller.get_filters,
            methods=["GET"],
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

    def test_set_values(self, air_client, test_data):
        values = {}
        values["mode"] = "A"
        result = air_client.set_values(values)
        data = test_data["http"]["status"]["data"]
        json_data = json.loads(data)
        assert result == json_data

    def test_set_wifi(self, air_client, test_data):
        result = air_client.set_wifi("1234", "5678")
        data = test_data["http"]["wifi"]["data"]
        json_data = json.loads(data)
        assert result == json_data

    def test_get_status_is_valid(self, air_client, test_data, controller):
        self.assert_json_data(air_client.get_status, "status", test_data)

    def test_get_wifi_is_valid(self, air_client, test_data):
        self.assert_json_data(air_client.get_wifi, "wifi", test_data)

    def test_get_firmware_is_valid(self, air_client, test_data):
        self.assert_json_data(air_client.get_firmware, "firmware", test_data)

    def test_get_filters_is_valid(self, air_client, test_data):
        self.assert_json_data(air_client.get_filters, "fltsts", test_data)

    def test_get_cli_status_is_valid(self, air_cli, test_data, capfd):
        self.assert_cli_data(air_cli.get_status, "status-cli", test_data, capfd)

    def test_get_cli_wifi_is_valid(self, air_cli, test_data, capfd):
        self.assert_cli_data(air_cli.get_wifi, "wifi-cli", test_data, capfd)

    def test_get_cli_firmware_is_valid(self, air_cli, test_data, capfd):
        self.assert_cli_data(air_cli.get_firmware, "firmware-cli", test_data, capfd)

    def test_get_cli_filters_is_valid(self, air_cli, test_data, capfd):
        self.assert_cli_data(air_cli.get_filters, "fltsts-cli", test_data, capfd)

    def test_set_values_cli_is_valid(self, air_cli, test_data, capfd):
        values = {}
        values["mode"] = "A"
        air_cli.set_values(values)
        result, err = capfd.readouterr()
        assert result == test_data["http"]["status-cli"]["data"]

    def assert_json_data(self, air_func, dataset, test_data):
        result = air_func()
        data = test_data["http"][dataset]["data"]
        json_data = json.loads(data)
        assert result == json_data

    def assert_cli_data(self, air_func, dataset, test_data, capfd):
        air_func()
        result, err = capfd.readouterr()
        assert result == test_data["http"][dataset]["data"]
