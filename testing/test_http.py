# pylint: disable=invalid-name, missing-class-docstring, missing-function-docstring

import os
import json
import pytest
from pyairctrl.http_client import HTTPAirClient
from pyairctrl.airctrl import ClientFactory
from testing.http_test_server import HttpTestServer
from testing.http_test_controller import HttpTestController
from pyairctrl.subset_enum import subsetEnum


class TestHTTP:
    device_key = "1234567890123456"

    @pytest.fixture(scope="class")
    def air_client(self):
        return HTTPAirClient("127.0.0.1")

    @pytest.fixture(scope="class")
    def air_cli(self):
        return ClientFactory.create("http", "127.0.0.1", False)

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
            "/di/v1/products/1/air",
            view_func=controller.get_status,
            methods=["GET"],
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

    def test_set_values(self, air_client):
        values = {}
        values["mode"] = "A"
        result = air_client.set_values(values)
        assert result

    def test_set_wifi(self, air_client):
        values = {}
        values["ssid"] = "1234"
        values["password"] = "5678"

        result = air_client.set_values(values, subsetEnum.wifi)
        assert result

    def test_get_information_is_valid(self, air_client, test_data, controller):
        self.assert_json_data(air_client.get_information, None, "status", test_data)

    def test_get_wifi_is_valid(self, air_client, test_data):
        self.assert_json_data(
            air_client.get_information, subsetEnum.wifi, "wifi", test_data
        )

    def test_get_firmware_is_valid(self, air_client, test_data):
        self.assert_json_data(
            air_client.get_information, subsetEnum.firmware, "firmware", test_data
        )

    def test_get_filters_is_valid(self, air_client, test_data):
        self.assert_json_data(
            air_client.get_information, subsetEnum.filter, "filter", test_data
        )

    def test_get_cli_status_is_valid(self, air_cli, test_data, capfd):
        self.assert_cli_data(
            air_cli.get_information, None, "status-cli", test_data, capfd
        )

    def test_get_cli_wifi_is_valid(self, air_cli, test_data, capfd):
        self.assert_cli_data(
            air_cli.get_information, subsetEnum.wifi, "wifi-cli", test_data, capfd
        )

    def test_get_cli_firmware_is_valid(self, air_cli, test_data, capfd):
        self.assert_cli_data(
            air_cli.get_information,
            subsetEnum.firmware,
            "firmware-cli",
            test_data,
            capfd,
        )

    def test_get_cli_filters_is_valid(self, air_cli, test_data, capfd):
        self.assert_cli_data(
            air_cli.get_information, subsetEnum.filter, "filter-cli", test_data, capfd
        )

    def assert_json_data(self, air_func, subset, dataset, test_data):
        result = air_func(subset)
        print(json.dumps(result))
        data = test_data["http"][dataset]["output"]
        json_data = json.loads(data)
        assert result == json_data

    def assert_cli_data(self, air_func, subset, dataset, test_data, capfd):
        air_func(subset)
        result, err = capfd.readouterr()
        print(result)
        assert result == test_data["http"][dataset]["output"]
