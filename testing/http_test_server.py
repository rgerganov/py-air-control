# pylint: disable=invalid-name, missing-class-docstring, missing-function-docstring

from multiprocessing import Process
import os
import time
import requests
import flask


class HttpTestServer:
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
