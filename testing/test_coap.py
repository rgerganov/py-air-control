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
from pyairctrl.coap_client import CoAPAirClient
from pyairctrl.airctrl import CoAPCli
from Cryptodome.Cipher import AES
from Cryptodome.Util.Padding import pad, unpad
import hashlib


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
        self.thread.join(5)

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
    SECRET_KEY = "JiangPan"

    def __init__(self, dataset, name="StatusResource"):
        super(StatusResource, self).__init__(name)
        self.dataset = dataset
        self.test_data = self._test_data()
        self.content_type = "application/json"
        self.encryption_key = ""

    def set_encryption_key(self, encryption_key):
        self.encryption_key = encryption_key

    def change_dataset(self, dataset):
        self.dataset = dataset

    def _test_data(self):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(dir_path, "data.json"), "r") as json_file:
            return json.load(json_file)

    def render_GET_advanced(self, request, response):
        response.payload = '{{"state":{{"reported": {} }} }}'.format(
            self.test_data[self.dataset]["data"]
        )
        response.payload = self._encrypt_payload(response.payload)
        return self, response

    def _encrypt_payload(self, payload):
        aes = self._handle_AES(self.encryption_key)
        paded_message = pad(bytes(payload.encode("utf8")), 16, style="pkcs7")
        encoded_message = aes.encrypt(paded_message).hex().upper()
        digest = self._create_digest(self.encryption_key, encoded_message)
        return self.encryption_key + encoded_message + digest

    def _handle_AES(self, id):
        key_and_iv = hashlib.md5((self.SECRET_KEY + id).encode()).hexdigest().upper()
        half_keylen = len(key_and_iv) // 2
        secret_key = key_and_iv[0:half_keylen]
        iv = key_and_iv[half_keylen:]
        return AES.new(
            bytes(secret_key.encode("utf8")), AES.MODE_CBC, bytes(iv.encode("utf8"))
        )

    def _create_digest(self, id, encoded_message):
        digest = (
            hashlib.sha256(bytes((id + encoded_message).encode("utf8")))
            .hexdigest()
            .upper()
        )
        return digest


class SyncResource(Resource):
    def __init__(self, name="SyncResource"):
        super(SyncResource, self).__init__(name)
        self.encryption_key = ""

    def render_POST_advanced(self, request, response):
        self.encryption_key = request.payload
        response.payload = "2170B935‬"
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


class TestCoap:
    @pytest.fixture(scope="class")
    def air_client(self):
        return CoAPAirClient("127.0.0.1")

    @pytest.fixture(scope="class")
    def air_cli(self):
        return CoAPCli("127.0.0.1")

    @pytest.fixture(scope="class")
    def test_data(self):
        return self._test_data()

    def _test_data(self):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(dir_path, "data.json"), "r") as json_file:
            return json.load(json_file)

    @pytest.fixture(scope="class")
    def sync_resource(self):
        return SyncResource()

    @pytest.fixture(scope="class")
    def status_resource(self):
        return StatusResource("coap-status")

    @pytest.fixture(scope="class", autouse=True)
    def coap_server(self, sync_resource, status_resource):
        server = CoAPServer(5683)
        server.add_url_rule("/sys/dev/status", status_resource)
        server.add_url_rule("/sys/dev/control", ControlResource('{"mode": "A"}'))
        server.add_url_rule("/sys/dev/sync", sync_resource)
        server.start()
        yield server
        server.stop()

    # def test_set_values(self, air_client):
    #     values = {}
    #     values["mode"] = "A"
    #     result = air_client.set_values(values)
    #     assert result

    def test_get_status_is_valid(
        self, sync_resource, status_resource, air_client, test_data
    ):
        self.assert_json_data(
            air_client.get_status,
            "coap-status",
            test_data,
            air_client,
            sync_resource,
            status_resource,
        )

    def test_get_firmware_is_valid(
        self, sync_resource, status_resource, air_client, test_data
    ):
        self.assert_json_data(
            air_client.get_firmware,
            "coap-status",
            test_data,
            air_client,
            sync_resource,
            status_resource,
        )

    def test_get_filters_is_valid(
        self, sync_resource, status_resource, air_client, test_data
    ):
        self.assert_json_data(
            air_client.get_filters,
            "coap-status",
            test_data,
            air_client,
            sync_resource,
            status_resource,
        )

    def test_get_cli_status_is_valid(
        self, sync_resource, status_resource, air_cli, test_data, capfd
    ):
        self.assert_cli_data(
            air_cli.get_status,
            "coap-status-cli",
            test_data,
            air_cli,
            capfd,
            sync_resource,
            status_resource,
        )

    def test_get_cli_status_err193_is_valid(
        self, sync_resource, status_resource, air_cli, test_data, capfd
    ):
        dataset = "coap-status-err193"
        status_resource.change_dataset(dataset)
        self.assert_cli_data(
            air_cli.get_status,
            "{}-cli".format(dataset),
            test_data,
            air_cli,
            capfd,
            sync_resource,
            status_resource,
        )

    def test_get_cli_firmware_is_valid(
        self, sync_resource, status_resource, air_cli, test_data, capfd
    ):
        self.assert_cli_data(
            air_cli.get_firmware,
            "coap-firmware-cli",
            test_data,
            air_cli,
            capfd,
            sync_resource,
            status_resource,
        )

    def test_get_cli_filters_is_valid(
        self, sync_resource, status_resource, air_cli, test_data, capfd
    ):
        self.assert_cli_data(
            air_cli.get_filters,
            "coap-fltsts-cli",
            test_data,
            air_cli,
            capfd,
            sync_resource,
            status_resource,
        )

    def assert_json_data(
        self, air_func, dataset, test_data, air_client, sync_resource, status_resource
    ):
        status_resource.set_encryption_key(sync_resource.encryption_key)

        result = air_func()
        data = test_data[dataset]["data"]
        json_data = json.loads(data)
        assert result == json_data

    def assert_cli_data(
        self,
        air_func,
        dataset,
        test_data,
        air_cli,
        capfd,
        sync_resource,
        status_resource,
    ):
        status_resource.set_encryption_key(sync_resource.encryption_key)

        air_func()
        result, err = capfd.readouterr()
        assert result == test_data[dataset]["data"]
