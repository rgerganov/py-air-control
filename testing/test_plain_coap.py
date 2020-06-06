# pylint: disable=invalid-name, missing-class-docstring, missing-function-docstring

import os
import json
import pytest
from pyairctrl.plain_coap_client import PlainCoAPAirClient
from pyairctrl.airctrl import PlainCoAPAirCli
from coap_test_server import CoAPTestServer
from plain_coap_resources import ControlResource, StatusResource


class TestPlainCoap:
    @pytest.fixture(scope="class")
    def air_client(self):
        return PlainCoAPAirClient("127.0.0.1")

    @pytest.fixture(scope="class")
    def air_cli(self):
        return PlainCoAPAirCli("127.0.0.1")

    @pytest.fixture(scope="class")
    def test_data(self):
        return self._test_data()

    @pytest.fixture(scope="class")
    def control_resource(self):
        return ControlResource()

    @pytest.fixture(scope="class")
    def status_resource(self):
        return StatusResource()

    @pytest.fixture(autouse=True)
    def set_defaults(self, control_resource, status_resource):
        control_resource.append_data('{"mode": "A"}')
        status_resource.set_dataset("status")

    def _test_data(self):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(dir_path, "data.json"), "r") as json_file:
            return json.load(json_file)

    @pytest.fixture(scope="class", autouse=True)
    def plain_coap_server(self, status_resource, control_resource):
        server = CoAPTestServer(5683)
        server.add_url_rule("/sys/dev/status", status_resource)
        server.add_url_rule("/sys/dev/control", control_resource)
        server.start()
        yield server
        server.stop()

    def test_set_values(self, air_client, monkeypatch):
        def send_hello_sequence(client):
            return

        monkeypatch.setattr(air_client, "_send_hello_sequence", send_hello_sequence)

        values = {}
        values["mode"] = "A"
        result = air_client.set_values(values)
        assert result

    def test_get_status_is_valid(self, air_client, test_data, monkeypatch):
        self.assert_json_data(
            air_client.get_status, "status", test_data, monkeypatch, air_client,
        )

    def test_get_firmware_is_valid(self, air_client, test_data, monkeypatch):
        self.assert_json_data(
            air_client.get_firmware, "status", test_data, monkeypatch, air_client,
        )

    def test_get_filters_is_valid(self, air_client, test_data, monkeypatch):
        self.assert_json_data(
            air_client.get_filters, "status", test_data, monkeypatch, air_client,
        )

    def test_get_cli_status_is_valid(self, air_cli, test_data, monkeypatch, capfd):
        self.assert_cli_data(
            air_cli.get_status, "status-cli", test_data, monkeypatch, air_cli, capfd,
        )

    def test_get_cli_firmware_is_valid(self, air_cli, test_data, monkeypatch, capfd):
        self.assert_cli_data(
            air_cli.get_firmware,
            "firmware-cli",
            test_data,
            monkeypatch,
            air_cli,
            capfd,
        )

    def test_get_cli_filters_is_valid(self, air_cli, test_data, monkeypatch, capfd):
        self.assert_cli_data(
            air_cli.get_filters, "fltsts-cli", test_data, monkeypatch, air_cli, capfd,
        )

    def assert_json_data(self, air_func, dataset, test_data, monkeypatch, air_client):
        def send_hello_sequence(client):
            return

        monkeypatch.setattr(air_client, "_send_hello_sequence", send_hello_sequence)

        result = air_func()
        data = test_data["plain-coap"][dataset]["data"]
        json_data = json.loads(data)
        assert result == json_data

    def assert_cli_data(
        self, air_func, dataset, test_data, monkeypatch, air_cli, capfd
    ):
        def send_hello_sequence(client):
            return

        monkeypatch.setattr(
            air_cli._client, "_send_hello_sequence", send_hello_sequence
        )

        air_func()
        result, err = capfd.readouterr()

        assert result == test_data["plain-coap"][dataset]["data"]
