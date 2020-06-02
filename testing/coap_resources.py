# pylint: disable=invalid-name, missing-class-docstring, missing-function-docstring
import os
import json
import hashlib
from Cryptodome.Cipher import AES
from Cryptodome.Util.Padding import pad, unpad
from coapthon.resources.resource import Resource


class SyncResource(Resource):
    SYNC_KEY = "2170B935‬"

    def __init__(self, name="SyncResource"):
        super(SyncResource, self).__init__(name)
        self.encryption_key = ""

    def render_POST_advanced(self, request, response):
        self.encryption_key = request.payload
        response.payload = self.SYNC_KEY
        return self, response


class StatusResource(Resource):
    SECRET_KEY = "JiangPan"

    def __init__(self, name="StatusResource"):
        super(StatusResource, self).__init__(name)
        self.dataset = None
        self.test_data = self._test_data()
        self.content_type = "application/json"
        self.encryption_key = None

    def set_encryption_key(self, encryption_key):
        self.encryption_key = encryption_key

    def set_dataset(self, dataset):
        self.dataset = dataset

    def _test_data(self):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(dir_path, "data.json"), "r") as json_file:
            return json.load(json_file)

    def render_GET_advanced(self, request, response):
        if self.dataset is None or self.encryption_key is None:
            raise Exception(
                "StatusResource: set dataset and encryption_key before running tests"
            )

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


class ControlResource(Resource):
    def __init__(self, name="ControlResource"):
        super(ControlResource, self).__init__(name)
        self.content_type = "application/json"
        self.data = []

    def append_data(self, data):
        self.data.append(data)

    def render_POST_advanced(self, request, response):
        if self.data.count == 0:
            raise Exception("ControlResource: set data before running tests")

        change_request = json.loads(request.payload)["state"]["desired"]

        success = "failed"
        for data in self.data:
            if json.loads(data) == change_request:
                success = "success"
                break

        response.payload = '{{"status":"{}"}}'.format(success)
        return self, response
