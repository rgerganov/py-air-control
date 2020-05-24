"""HTTP Client."""

# pylint: disable=invalid-name, missing-class-docstring, missing-function-docstring

import base64
import binascii
import configparser
import json
import os
import random
import socket
import urllib.request
import xml.etree.ElementTree as ET

from Cryptodome.Cipher import AES
from Cryptodome.Util.Padding import pad, unpad

G = int(
    "A4D1CBD5C3FD34126765A442EFB99905F8104DD258AC507FD6406CFF14266D31266FEA1E5C41564B777E690F5504F213160217B4B01B886A5E91547F9E2749F4D7FBD7D3B9A92EE1909D0D2263F80A76A6A24C087A091F531DBF0A0169B6A28AD662A4D18E73AFA32D779D5918D08BC8858F4DCEF97C2A24855E6EEB22B3B2E5",
    16,
)
P = int(
    "B10B8F96A080E01DDE92DE5EAE5D54EC52C99FBCFB06A3C69A6A9DCA52D23B616073E28675A23D189838EF1E2EE652C013ECB4AEA906112324975C3CD49B83BFACCBDD7D90C4BD7098488E9C219A73724EFFD6FAE5644738FAA31A4FF55BCCC0A151AF5F0DC8B4BD45BF37DF365C1A65E68CFDA76D4DA708DF1FB2BC2E4A4371",
    16,
)


def aes_decrypt(data, key):
    iv = bytes(16)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return cipher.decrypt(data)


def encrypt(values, key):
    # add two random bytes in front of the body
    data = "AA" + json.dumps(values)
    data = pad(bytearray(data, "ascii"), 16, style="pkcs7")
    iv = bytes(16)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    data_enc = cipher.encrypt(data)
    return base64.b64encode(data_enc)


def decrypt(data, key):
    payload = base64.b64decode(data)
    data = aes_decrypt(payload, key)
    # response starts with 2 random bytes, exclude them
    response = unpad(data, 16, style="pkcs7")[2:]
    return response.decode("ascii")


class HTTPAirClient:
    @staticmethod
    def ssdp(timeout=1, repeats=3):
        addr = "239.255.255.250"
        port = 1900
        msg = "\r\n".join(
            [
                "M-SEARCH * HTTP/1.1",
                "HOST: {}:{}".format(addr, port),
                "ST: urn:philips-com:device:DiProduct:1",
                "MX: 1",
                'MAN: "ssdp:discover"',
                "",
                "",
            ]
        ).encode("ascii")
        urls = {}
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            s.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_TTL, 20)
            s.settimeout(timeout)
            for i in range(repeats):
                s.sendto(msg, (addr, port))
                try:
                    while True:
                        data, (ip, _) = s.recvfrom(1024)
                        url = next(
                            (
                                x
                                for x in data.decode("ascii").splitlines()
                                if x.startswith("LOCATION: ")
                            ),
                            None,
                        )
                        urls.update({ip: url[10:]})
                except socket.timeout:
                    pass
                if len(urls):
                    break
        resp = []
        for ip in urls.keys():
            with urllib.request.urlopen(urls[ip]) as response:
                xml = ET.fromstring(response.read())
                resp.append({"ip": ip})
                ns = {"urn": "urn:schemas-upnp-org:device-1-0"}
                for d in xml.findall("urn:device", ns):
                    for t in ["modelName", "modelNumber", "friendlyName"]:
                        resp[-1].update({t: d.find("urn:" + t, ns).text})

        return resp

    def __init__(self, host):
        self._host = host
        self._session_key = None

    def _get_key(self):
        print("Exchanging secret key with the device ...")
        url = "http://{}/di/v1/products/0/security".format(self._host)
        a = random.getrandbits(256)
        A = pow(G, a, P)
        data = json.dumps({"diffie": format(A, "x")})
        data_enc = data.encode("ascii")
        req = urllib.request.Request(url=url, data=data_enc, method="PUT")
        with urllib.request.urlopen(req) as response:
            resp = response.read().decode("ascii")
            dh = json.loads(resp)
        key = dh["key"]
        B = int(dh["hellman"], 16)
        s = pow(B, a, P)
        s_bytes = s.to_bytes(128, byteorder="big")[:16]
        session_key = aes_decrypt(bytes.fromhex(key), s_bytes)
        self._session_key = session_key[:16]
        self._save_key()

    def _save_key(self):
        config = configparser.ConfigParser()
        fpath = os.path.expanduser("~/.pyairctrl")
        config.read(fpath)
        if "keys" not in config.sections():
            config["keys"] = {}
        hex_key = binascii.hexlify(self._session_key).decode("ascii")
        config["keys"][self._host] = hex_key
        print("Saving session_key {} to {}".format(hex_key, fpath))
        with open(fpath, "w") as f:
            config.write(f)

    def load_key(self):
        fpath = os.path.expanduser("~/.pyairctrl")
        if os.path.isfile(fpath):
            config = configparser.ConfigParser()
            config.read(fpath)
            if "keys" in config and self._host in config["keys"]:
                hex_key = config["keys"][self._host]
                self._session_key = bytes.fromhex(hex_key)
                self._check_key()
            else:
                self._get_key()
        else:
            self._get_key()

    def _check_key(self):
        url = "http://{}/di/v1/products/1/air".format(self._host)
        self._get(url)

    def set_values(self, values):
        body = encrypt(values, self._session_key)
        url = "http://{}/di/v1/products/1/air".format(self._host)
        req = urllib.request.Request(url=url, data=body, method="PUT")
        with urllib.request.urlopen(req) as response:
            resp = response.read()
            resp = decrypt(resp.decode("ascii"), self._session_key)
            status = json.loads(resp)
            return status

    def set_wifi(self, ssid, pwd):
        values = {}
        if ssid:
            values["ssid"] = ssid
        if pwd:
            values["password"] = pwd

        body = encrypt(values, self._session_key)
        url = "http://{}/di/v1/products/0/wifi".format(self._host)
        req = urllib.request.Request(url=url, data=body, method="PUT")
        with urllib.request.urlopen(req) as response:
            resp = response.read()
            resp = decrypt(resp.decode("ascii"), self._session_key)
            wifi = json.loads(resp)
            return wifi

    def _get_once(self, url):
        with urllib.request.urlopen(url) as response:
            resp = response.read()
            resp = decrypt(resp.decode("ascii"), self._session_key)
            return json.loads(resp)

    def _get(self, url):
        try:
            return self._get_once(url)
        except Exception as e:
            print("GET error: {}".format(str(e)))
            print("Will retry after getting a new key ...")
            self._get_key()
            return self._get_once(url)

    def get_status(self):
        url = "http://{}/di/v1/products/1/air".format(self._host)
        status = self._get(url)
        return status

    def get_wifi(self):
        url = "http://{}/di/v1/products/0/wifi".format(self._host)
        wifi = self._get(url)
        return wifi

    def get_firmware(self):
        url = "http://{}/di/v1/products/0/firmware".format(self._host)
        firmware = self._get(url)
        return firmware

    def get_filters(self):
        url = "http://{}/di/v1/products/1/fltsts".format(self._host)
        filters = self._get(url)
        return filters

    def pair(self, client_id, client_secret):
        values = {}
        values["Pair"] = ["FI-AIR-AND", client_id, client_secret]
        body = encrypt(values, self._session_key)
        url = "http://{}/di/v1/products/0/pairing".format(self._host)
        req = urllib.request.Request(url=url, data=body, method="PUT")
        with urllib.request.urlopen(req) as response:
            resp = response.read()
            resp = decrypt(resp.decode("ascii"), self._session_key)
            resp = json.loads(resp)
            return resp
