# pylint: disable=invalid-name, missing-class-docstring, missing-function-docstring

from threading import Thread
import os
import json
import time
import pytest
from coapthon.server.coap import CoAP
from coapthon.client.helperclient import HelperClient
from coapthon.resources.resource import Resource
from coapthon import defines
from pyairctrl.plain_coap_client import PlainCoAPAirClient
from pyairctrl.airctrl import PlainCoAPAirCli


class CoAPServer:
    def __init__(self, port):
        super().__init__()
        self.coap_server = CoAP(("127.0.0.1", port))
        self.client = HelperClient(server=("127.0.0.1", port))
        self.add_url_rule("testing", CoapTestResource())
        self.thread = Thread(target=self._run)

    def _test_connection(self):
        try:
            request = self.client.mk_request(defines.Codes.GET, "testing")
            response = self.client.send_request(request, None, 2)
            if response.payload == "success":
                return True
            else:
                return False
        except Exception as e:
            return True

    def _run(self):
        self.coap_server.listen(5)

    def start(self):
        self.thread.start()
        while not self._test_connection():
            time.sleep(1)

    def stop(self):
        self.coap_server.close()
        self.client.close()
        # self.thread.join(5)

    def add_url_rule(self, path, resource):
        assert isinstance(resource, Resource)
        path = path.strip("/")
        paths = path.split("/")
        actual_path = ""
        i = 0
        for p in paths:
            i += 1
            actual_path += "/" + p
            try:
                res = self.coap_server.root[actual_path]
            except KeyError:
                res = None
            if res is None:
                resource.path = actual_path
                self.coap_server.root[actual_path] = resource

        # TODO: Code can be removed after Coapthon3 > 1.01 is ready and imported, add code below instead
        # self.coap_server.add_resource(rule, resource)


class CoapTestResource(Resource):
    def __init__(self, name="CoapTestResource"):
        super(CoapTestResource, self).__init__(name)
        self.payload = "success"

    def render_GET(self, request):
        return self


class StatusResource(Resource):
    def __init__(self, dataset, name="StatusResource"):
        super(StatusResource, self).__init__(name)
        self.dataset = dataset
        self.test_data = self._test_data()
        self.content_type = "application/json"

    def _test_data(self):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(dir_path, "data.json"), "r") as json_file:
            return json.load(json_file)

    def render_GET_advanced(self, request, response):
        response.payload = '{{"state":{{"reported": {} }} }}'.format(
            self.test_data[self.dataset]["data"]
        )
        return self, response


class ControlResource(Resource):
    def __init__(self, data, name="ControlResource"):
        super(ControlResource, self).__init__(name)
        self.content_type = "application/json"
        self.data = data

    def render_POST_advanced(self, request, response):
        change_request = json.loads(request.payload)["state"]["desired"]

        success = "success" if json.loads(self.data) == change_request else "failed"
        response.payload = '{{"status":"{}"}}'.format("success")
        return self, response


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

    def _test_data(self):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(dir_path, "data.json"), "r") as json_file:
            return json.load(json_file)

    @pytest.fixture(scope="class", autouse=True)
    def plain_coap_server(self):
        server = CoAPServer(5683)
        server.add_url_rule("/sys/dev/status", StatusResource("plain-coap-status"))
        server.add_url_rule("/sys/dev/control", ControlResource('{"mode": "A"}'))
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
            air_client.get_status,
            "plain-coap-status",
            test_data,
            monkeypatch,
            air_client,
        )

    def test_get_firmware_is_valid(self, air_client, test_data, monkeypatch):
        self.assert_json_data(
            air_client.get_firmware,
            "plain-coap-status",
            test_data,
            monkeypatch,
            air_client,
        )

    def test_get_filters_is_valid(self, air_client, test_data, monkeypatch):
        self.assert_json_data(
            air_client.get_filters,
            "plain-coap-status",
            test_data,
            monkeypatch,
            air_client,
        )

    def test_get_cli_status_is_valid(self, air_cli, test_data, monkeypatch, capfd):
        self.assert_cli_data(
            air_cli.get_status,
            "plain-coap-status-cli",
            test_data,
            monkeypatch,
            air_cli,
            capfd,
        )

    def test_get_cli_firmware_is_valid(self, air_cli, test_data, monkeypatch, capfd):
        self.assert_cli_data(
            air_cli.get_firmware,
            "plain-coap-firmware-cli",
            test_data,
            monkeypatch,
            air_cli,
            capfd,
        )

    def test_get_cli_filters_is_valid(self, air_cli, test_data, monkeypatch, capfd):
        self.assert_cli_data(
            air_cli.get_filters,
            "plain-coap-fltsts-cli",
            test_data,
            monkeypatch,
            air_cli,
            capfd,
        )

    def assert_json_data(self, air_func, dataset, test_data, monkeypatch, air_client):
        def send_hello_sequence(client):
            return

        monkeypatch.setattr(air_client, "_send_hello_sequence", send_hello_sequence)

        result = air_func()
        data = test_data[dataset]["data"]
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
        assert result == test_data[dataset]["data"]
