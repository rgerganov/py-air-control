# pylint: disable=invalid-name, missing-class-docstring, missing-function-docstring

import os
import json
from coapthon.resources.resource import Resource


class StatusResource(Resource):
    def __init__(self, name="StatusResource"):
        super(StatusResource, self).__init__(name)
        self.dataset = None
        self.test_data = self._test_data()
        self.content_type = "application/json"

    def _test_data(self):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(dir_path, "data.json"), "r") as json_file:
            return json.load(json_file)

    def set_dataset(self, dataset):
        self.dataset = dataset

    def render_GET_advanced(self, request, response):
        if self.dataset is None:
            raise Exception("StatusResource: set dataset before running tests")

        response.payload = '{{"state":{{"reported": {} }} }}'.format(
            self.test_data[self.dataset]["data"]
        )
        return self, response


class ControlResource(Resource):
    def __init__(self, name="ControlResource"):
        super(ControlResource, self).__init__(name)
        self.content_type = "application/json"
        self.data = None

    def set_data(self, data):
        self.data = data

    def render_POST_advanced(self, request, response):
        if self.data is None:
            raise Exception("ControlResource: set data before running tests")

        change_request = json.loads(request.payload)["state"]["desired"]

        success = "success" if json.loads(self.data) == change_request else "failed"
        response.payload = '{{"status":"{}"}}'.format("success")
        return self, response
