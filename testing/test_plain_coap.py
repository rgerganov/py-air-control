# pylint: disable=invalid-name, missing-class-docstring, missing-function-docstring

import os
import json
from pyairctrl.base_client import NotSupportedException
import pytest
from pyairctrl.plain_coap_client import PlainCoAPAirClient
from pyairctrl.airctrl import ClientFactory
from testing.coap_test_server import CoAPTestServer
from testing.plain_coap_resources import ControlResource, StatusResource
from pyairctrl.subset_enum import subsetEnum


class TestPlainCoap:
    @pytest.fixture(scope="class")
    def monkeyclass(self):
        from _pytest.monkeypatch import MonkeyPatch

        mpatch = MonkeyPatch()
        yield mpatch
        mpatch.undo()

    @pytest.fixture(scope="class")
    def air_client(self, monkeyclass):
        def initConnection(client):
            return

        monkeyclass.setattr(PlainCoAPAirClient, "_initConnection", initConnection)
        return PlainCoAPAirClient("127.0.0.1")

    @pytest.fixture(scope="class")
    def air_cli(self):
        return ClientFactory.create("plain_coap", "127.0.0.1", False)

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

    def test_set_values(self, air_client):
        values = {}
        values["mode"] = "A"
        result = air_client.set_values(values)
        assert result

    def test_set_wifi_isnotsupported(self, air_client):
        values = {}
        values["ssid"] = "1234"
        values["password"] = "5678"

        with pytest.raises(NotSupportedException) as excinfo:
            result = air_client.set_values(values, subsetEnum.wifi)

        assert (
            "Setting wifi credentials is currently not supported when using CoAP. Use the app instead."
            in str(excinfo.value)
        )

    def test_get_information_is_valid(self, air_client, test_data):
        self.assert_json_data(
            air_client.get_information,
            None,
            "status",
            test_data,
            air_client,
        )

    def test_get_wifi_is_isnotsupported(self, air_client):
        with pytest.raises(NotSupportedException) as excinfo:
            air_client.get_information(subsetEnum.wifi)

        assert (
            "Getting wifi credentials is currently not supported when using CoAP. Use the app instead."
            in str(excinfo.value)
        )

    def test_get_firmware_is_valid(self, air_client, test_data):
        self.assert_json_data(
            air_client.get_information,
            subsetEnum.firmware,
            "firmware",
            test_data,
            air_client,
        )

    def test_get_filters_is_valid(self, air_client, test_data):
        self.assert_json_data(
            air_client.get_information,
            subsetEnum.filter,
            "filter",
            test_data,
            air_client,
        )

    def test_get_cli_status_is_valid(self, air_cli, test_data, capfd):
        self.assert_cli_data(
            air_cli.get_information,
            None,
            "status-cli",
            test_data,
            air_cli,
            capfd,
        )

    def test_get_cli_firmware_is_valid(self, air_cli, test_data, capfd):
        self.assert_cli_data(
            air_cli.get_information,
            subsetEnum.firmware,
            "firmware-cli",
            test_data,
            air_cli,
            capfd,
        )

    def test_get_cli_filters_is_valid(self, air_cli, test_data, capfd):
        self.assert_cli_data(
            air_cli.get_information,
            subsetEnum.filter,
            "filter-cli",
            test_data,
            air_cli,
            capfd,
        )

    def assert_json_data(self, air_func, subset, dataset, test_data, air_client):
        result = air_func(subset)
        data = test_data["plain-coap"][dataset]["output"]
        json_data = json.loads(data)
        assert result == json_data

    def assert_cli_data(self, air_func, subset, dataset, test_data, air_cli, capfd):
        air_func(subset)
        result, err = capfd.readouterr()

        assert result == test_data["plain-coap"][dataset]["output"]
