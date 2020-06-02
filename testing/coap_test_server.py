# pylint: disable=invalid-name, missing-class-docstring, missing-function-docstring

from threading import Thread
import time
from coapthon.server.coap import CoAP
from coapthon.client.helperclient import HelperClient
from coapthon.resources.resource import Resource
from coapthon import defines


class CoAPTestServer:
    def __init__(self, port):
        super().__init__()
        self.coap_server = CoAP(("127.0.0.1", port))
        self.client = HelperClient(server=("127.0.0.1", port))
        self.add_url_rule("testCoapIsAlive", CoapTestResource())
        self.thread = Thread(target=self._run)

    def _test_connection(self):
        try:
            request = self.client.mk_request(defines.Codes.GET, "testCoapIsAlive")
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
