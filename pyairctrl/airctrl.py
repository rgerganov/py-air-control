#!/usr/bin/env python3
from Cryptodome.Cipher import AES
from Cryptodome.Util.Padding import pad, unpad
from coapthon.client.helperclient import HelperClient
from coapthon import defines
from coapthon.messages.request import Request
from coapthon.utils import generate_random_token
import urllib.request
import base64
import binascii
import argparse
import json
import random
import os
import sys
import pprint
import configparser
import socket
import xml.etree.ElementTree as ET
import struct
import time
import logging
from abc import ABC, abstractmethod
import hashlib

G = int('A4D1CBD5C3FD34126765A442EFB99905F8104DD258AC507FD6406CFF14266D31266FEA1E5C41564B777E690F5504F213160217B4B01B886A5E91547F9E2749F4D7FBD7D3B9A92EE1909D0D2263F80A76A6A24C087A091F531DBF0A0169B6A28AD662A4D18E73AFA32D779D5918D08BC8858F4DCEF97C2A24855E6EEB22B3B2E5', 16)
P = int('B10B8F96A080E01DDE92DE5EAE5D54EC52C99FBCFB06A3C69A6A9DCA52D23B616073E28675A23D189838EF1E2EE652C013ECB4AEA906112324975C3CD49B83BFACCBDD7D90C4BD7098488E9C219A73724EFFD6FAE5644738FAA31A4FF55BCCC0A151AF5F0DC8B4BD45BF37DF365C1A65E68CFDA76D4DA708DF1FB2BC2E4A4371', 16)

def aes_decrypt(data, key):
    iv = bytes(16)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return cipher.decrypt(data)

def encrypt(values, key):
    # add two random bytes in front of the body
    data = 'AA' + json.dumps(values)
    data = pad(bytearray(data, 'ascii'), 16, style='pkcs7')
    iv = bytes(16)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    data_enc = cipher.encrypt(data)
    return base64.b64encode(data_enc)

def decrypt(data, key):
    payload = base64.b64decode(data)
    data = aes_decrypt(payload, key)
    # response starts with 2 random bytes, exclude them
    response = unpad(data, 16, style='pkcs7')[2:]
    return response.decode('ascii')

statusTransformer = {
    "name" : ("Name: {}", None),
    "type" : ("Type: {}", None),
    "modelid" : ("ModelId: {}", None),
    "swversion" : ("Version: {}", None),
    "StatusType" : ("StatusType: {}", None),
    "ota" : ("Over the air updates: {}", None),
    "StatusType" : ("StatusType: {}", None),
    "Runtime" : ("Runtime: {} hours", lambda runtime: round(((runtime/(1000*60*60))%24), 2)),
    "pwr" : ("Power: {}", lambda pwr: {'1': 'ON', '0': 'OFF'}.get(pwr, pwr)),
    "pm25" : ("PM25: {}", None),
    "rh" : ("Humidity: {}", None),
    "rhset" : ("Target humidity: {}", None),
    "iaql" : ("Allergen index: {}", None),
    "temp" : ("Temperature: {}", None),
    "func" : ("Function: {}", lambda func: {'P': 'Purification', 'PH': 'Purification & Humidification'}.get(func, func)),
    "mode" : ("Mode: {}", lambda mode: {'P': 'auto', 'A': 'allergen', 'S': 'sleep', 'M': 'manual', 'B': 'bacteria', 'N': 'night'}.get(mode, mode)),
    "om" : ("Fan speed: {}", lambda om: {'s': 'silent', 't': 'turbo'}.get(om, om)),
    "aqil" : ("Light brightness: {}", None),
    "aqit" : ("Air quality notification threshold: {}", None),
    "uil" : ("Buttons light: {}", lambda uil: {'1': 'ON', '0': 'OFF'}.get(uil, uil)),
    "ddp" : ("Used index: {}", lambda ddp: {'3': 'Humidity', '1': 'PM2.5', '0': 'IAI'}.get(ddp, ddp)),
    "wl" : ("Water level: {}", None),
    "cl" : ("Child lock: {}", None),
    "dt" : ("Timer: {} hours", lambda dt: None if dt == 0 else dt),
    "dtrs" : ("Timer: {} minutes left", lambda dtrs: None if dtrs == 0 else dtrs),
    "fltt1" : ("HEPA filter type: {}", lambda fltt1: {'A3': 'NanoProtect Filter Series 3 (FY2422)'}.get(fltt1, fltt1)),
    "fltt2" : ("Active carbon filter type: {}", lambda fltt2: {'C7': 'NanoProtect Filter AC (FY2420)'}.get(fltt2, fltt2)),
    "fltsts0" : ("Pre-filter and Wick: clean in {} hours", None),
    "fltsts1" : ("HEPA filter: replace in {} hours", None),
    "fltsts2" : ("Active carbon filter: replace in {} hours", None),
    "wicksts" : ("Wick filter: replace in {} hours", None),
    "err" : ("[ERROR] Message: {}", lambda err: None if err == 0 else {49408: 'no water', 32768: 'water tank open', 49155: 'pre-filter must be cleaned'}.get(err, err)),
}

class AirClientBase(ABC):
    def __init__(self, host, port, debug=False):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel("WARN")
        self.server = host
        self.port = port
        self.debug = debug

    def _get_info_for_key(self, key, current_value):
        if key in statusTransformer:
            info = statusTransformer[key]
            if not info[1] is None:
                current_value = info[1](current_value)
                if current_value is None:
                    return None
            return info[0].format(current_value)
        else:
            return '{}: {}'.format(key, current_value)

    def _dump_status(self, status, debug=False):
        if debug==True:
            print("Raw status:")
            pprint.pprint(status)
        for key in status:
            current_value=status[key]
            name_and_value=self._get_info_for_key(key, current_value)
            if name_and_value is None:
                continue

            print('[{key}]\t{name_and_value}'.format(key=key, name_and_value=name_and_value).expandtabs(30))

    def get_status(self, debug=False):
        if debug:
            self.logger.setLevel("DEBUG")
        status = self._get('air')
        if status is not None:
            return self._dump_status(status, debug=debug)

    def set_values(self, values, debug=False):
        if debug:
            self.logger.setLevel("DEBUG")
        for key in values:
            self._set(key, values[key])

    @abstractmethod
    def _get(self, param):
        pass

    @abstractmethod
    def _set(self, key, value):
        pass

    def get_firmware(self):
        status = self._get('firmware')
        if status is None:
            print("No version-info found")
            return

        print(self._get_info_for_key("swversion", status["swversion"] if "swversion" in status else "nA"))
        print(self._get_info_for_key("ota", status["ota"] if "ota" in status else "nA"))

    def get_filters(self):
        status = self._get('fltsts')
        if status is None:
            print("No version-info found")
            return

        if "fltsts0" in status: print(self._get_info_for_key("fltsts0", status["fltsts0"]))
        if "fltsts1" in status: print(self._get_info_for_key("fltsts1", status["fltsts1"]))
        if "fltsts2" in status: print(self._get_info_for_key("fltsts2", status["fltsts2"]))
        if "wicksts" in status: print(self._get_info_for_key("wicksts", status["wicksts"]))

class HTTPAirClient(AirClientBase):

    @staticmethod
    def ssdp(timeout=1, repeats=3, debug=False):
        addr = '239.255.255.250'
        port = 1900
        msg = '\r\n'.join([
            'M-SEARCH * HTTP/1.1',
            'HOST: {}:{}'.format(addr, port),
            'ST: urn:philips-com:device:DiProduct:1',
            'MX: 1', 'MAN: "ssdp:discover"','', '']).encode('ascii')
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
                        url = next((x for x in data.decode('ascii').splitlines() if x.startswith('LOCATION: ')), None)
                        urls.update({ip: url[10:]})
                except socket.timeout:
                    pass
                if len(urls): break
        resp = []
        for ip in urls.keys():
            with urllib.request.urlopen(urls[ip]) as response:
                xml = ET.fromstring(response.read())
                resp.append({'ip': ip})
                ns = {'urn': 'urn:schemas-upnp-org:device-1-0'}
                for d in xml.findall('urn:device', ns):
                    for t in ['modelName', 'modelNumber', 'friendlyName']:
                        resp[-1].update({t: d.find('urn:'+t, ns).text})
        if debug:
            pprint.pprint(resp)
        return resp

    def __init__(self, host, port=80, debug=False):
        super().__init__(host, port, debug)
        self._session_key = None

    def _get_key(self):
        print('Exchanging secret key with the device ...')
        url = 'http://{}/di/v1/products/0/security'.format(self.server)
        a = random.getrandbits(256)
        A = pow(G, a, P)
        data = json.dumps({'diffie': format(A, 'x')})
        data_enc = data.encode('ascii')
        req = urllib.request.Request(url=url, data=data_enc, method='PUT')
        with urllib.request.urlopen(req) as response:
            resp = response.read().decode('ascii')
            dh = json.loads(resp)
        key = dh['key']
        B = int(dh['hellman'], 16)
        s = pow(B, a, P)
        s_bytes = s.to_bytes(128, byteorder='big')[:16]
        session_key = aes_decrypt(bytes.fromhex(key), s_bytes)
        self._session_key = session_key[:16]
        self._save_key()

    def _save_key(self):
        config = configparser.ConfigParser()
        fpath = os.path.expanduser('~/.pyairctrl')
        config.read(fpath)
        if 'keys' not in config.sections():
            config['keys'] = {}
        hex_key = binascii.hexlify(self._session_key).decode('ascii')
        config['keys'][self.server] = hex_key
        print("Saving session_key {} to {}".format(hex_key, fpath))
        with open(fpath, 'w') as f:
            config.write(f)

    def load_key(self):
        fpath = os.path.expanduser('~/.pyairctrl')
        if os.path.isfile(fpath):
            config = configparser.ConfigParser()
            config.read(fpath)
            if 'keys' in config and self.server in config['keys']:
                hex_key = config['keys'][self.server]
                self._session_key = bytes.fromhex(hex_key)
                self._check_key()
            else:
                self._get_key()
        else:
            self._get_key()

    def _check_key(self):
        url = 'http://{}/di/v1/products/1/air'.format(self.server)
        self._get(url)

    def set_values(self, values, debug=False):
        body = encrypt(values, self._session_key)
        url = 'http://{}/di/v1/products/1/air'.format(self.server)
        req = urllib.request.Request(url=url, data=body, method='PUT')
        try:
            with urllib.request.urlopen(req) as response:
                resp = response.read()
                resp = decrypt(resp.decode('ascii'), self._session_key)
                status = json.loads(resp)
                self._dump_status(status, debug=debug)
        except urllib.error.HTTPError as e:
            print("Error setting values (response code: {})".format(e.code))


    def set_wifi(self, ssid, pwd):
        values = {}
        if ssid:
            values['ssid'] = ssid
        if pwd:
            values['password'] = pwd
        pprint.pprint(values)
        body = encrypt(values, self._session_key)
        url = 'http://{}/di/v1/products/0/wifi'.format(self.server)
        req = urllib.request.Request(url=url, data=body, method='PUT')
        with urllib.request.urlopen(req) as response:
            resp = response.read()
            resp = decrypt(resp.decode('ascii'), self._session_key)
            wifi = json.loads(resp)
            pprint.pprint(wifi)

    def _get_once(self, url):
        with urllib.request.urlopen(url) as response:
            resp = response.read()
            resp = decrypt(resp.decode('ascii'), self._session_key)
            return json.loads(resp)

    def _get(self, param):
        url = 'http://{}/di/v1/products/1/{}'.format(self.server, param)
        try:
            return self._get_once(url)
        except Exception as e:
            print("GET error: {}".format(str(e)))
            print("Will retry after getting a new key ...")
            self._get_key()
            return self._get_once(url)

    def get_wifi(self):
        wifi = self._get('wifi')
        pprint.pprint(wifi)

    def pair(self, client_id, client_secret):
        values = {}
        values['Pair'] = ['FI-AIR-AND', client_id, client_secret]
        body = encrypt(values, self._session_key)
        url = 'http://{}/di/v1/products/0/pairing'.format(self.server)
        req = urllib.request.Request(url=url, data=body, method='PUT')
        with urllib.request.urlopen(req) as response:
            resp = response.read()
            resp = decrypt(resp.decode('ascii'), self._session_key)
            resp = json.loads(resp)
            pprint.pprint(resp)

class CoAPAirClient(AirClientBase):
    def __init__(self, host, port = 5683, debug=False):
        super().__init__(host, port, debug)
        self.client = self._create_coap_client(self.server, self.port)

    def get_wifi(self):
        print("Getting wifi credentials is currently not supported when using CoAP. Use the app instead.")

    def set_wifi(self, ssid, pwd):
        print("Setting wifi credentials is currently not supported when using CoAP. Use the app instead.")

    def _create_coap_client(self, host, port):
        return HelperClient(server=(host, port))

class Version021Client(CoAPAirClient):
    def __init__(self, host, port=5683, debug=False):
        super().__init__(host, port, debug)
        self._send_hello_sequence()

    def _send_over_socket(self, destination, packet):
        protocol = socket.getprotobyname('icmp')
        if os.geteuid()==0:
            s = socket.socket(socket.AF_INET, socket.SOCK_RAW, protocol)
        else:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, protocol)
        try:
            s.sendto(packet, (destination, 0))
        except OSError: # That fixes a mac os bug for me: OSError: [Errno 22] Invalid argument
            None
        finally:
            s.close()

    def _get(self, param):
        path ="/sys/dev/status"
        try:
            request = self.client.mk_request(defines.Codes.GET, path)
            request.destination = server=(self.server, self.port)
            request.type = defines.Types["ACK"]
            request.token = generate_random_token(4)
            request.observe = 0
            response = self.client.send_request(request, None, 2)
        finally:
            self.client.stop()

        if response:
            return json.loads(response.payload)["state"]["reported"]
        else:
            return {}

    def _set(self, key, value):
        path = "/sys/dev/control"
        try:
            payload = { "state" : { "desired" : { key: value } } }
            self.client.post(path, json.dumps(payload))
        finally:
            self.client.stop()

    def _send_hello_sequence(self):
        ownIp = self._get_ip()

        header = self._create_icmp_header()
        data = self._create_icmp_data(ownIp, self.port, self.server, self.port)
        packet = header + data
        packet = self._create_icmp_header(self._checksum_icmp(packet)) + data

        self._send_over_socket(self.server, packet)

        # that is needed to give device time to open coap port, otherwise it may not respond properly
        time.sleep(0.5)

        request = Request()
        request.destination = server=(self.server, self.port)
        request.code = defines.Codes.EMPTY.number
        self.client.send_empty(request)

    def _get_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # doesn't even have to be reachable
            s.connect(('10.255.255.255', 1))
            IP = s.getsockname()[0]
        except:
            IP = '127.0.0.1'
        finally:
            s.close()
        return IP

    def _checksum_icmp(self, source_string):
        countTo = (int(len(source_string) / 2)) * 2
        sum = 0
        count = 0
        loByte = 0
        hiByte = 0
        while count < countTo:
            if (sys.byteorder == "little"):
                loByte = source_string[count]
                hiByte = source_string[count + 1]
            else:
                loByte = source_string[count + 1]
                hiByte = source_string[count]
            sum = sum + (hiByte * 256 + loByte)
            count += 2

        if countTo < len(source_string): # Check for odd length
            loByte = source_string[len(source_string) - 1]
            sum += loByte

        sum &= 0xffffffff
        sum = (sum >> 16) + (sum & 0xffff)
        sum += (sum >> 16)
        answer = ~sum & 0xffff
        answer = socket.htons(answer)
        return answer

    def _create_icmp_header(self, checksum=0):
        ICMP_TYPE = 3
        ICMP_CODE = 3
        UNUSED = 0
        CHECKSUM = checksum
        header = struct.pack(
            "!BBHI", ICMP_TYPE, ICMP_CODE, CHECKSUM, UNUSED
        )
        return header

    def _checksum_tcp(self, pkt):
        return 0 # looks like its irrelevant what we send here

    def _create_tcp_data(self, srcIp, dstIp, checksum=0):
        ip_version = 4
        ip_vhl = 5

        ip_ver = (ip_version << 4 ) + ip_vhl

        # Differentiate Service Field
        ip_dsc = 0
        ip_ecn = 0

        ip_dfc = (ip_dsc << 2 ) + ip_ecn

        # Total Length
        ip_tol = 214

        # Identification
        ip_idf = 6190

        # Flags
        ip_rsv = 0
        ip_dtf = 0
        ip_mrf = 0
        ip_frag_offset = 0

        ip_flg = (ip_rsv << 7) + (ip_dtf << 6) + (ip_mrf << 5) + (ip_frag_offset)

        # Time to live
        ip_ttl = 255

        # Protocol
        ip_proto = socket.IPPROTO_UDP

        # Check Sum
        ip_chk = checksum

        # Source Address
        ip_saddr = socket.inet_aton(srcIp)

        # Destination Address
        ip_daddr = socket.inet_aton(dstIp)
        tcp = struct.pack('!BBHHHBBH4s4s' ,
            ip_ver,   # IP Version
            ip_dfc,   # Differentiate Service Feild
            ip_tol,   # Total Length
            ip_idf,   # Identification
            ip_flg,   # Flags
            ip_ttl,   # Time to leave
            ip_proto, # protocol
            ip_chk,   # Checksum
            ip_saddr, # Source IP
            ip_daddr  # Destination IP
        )
        return tcp

    def _create_udp_data(self, srcPort, dstPort):
        data = 0
        sport = srcPort
        dport = dstPort
        length = 194
        checksum = 0
        udp = struct.pack('!HHHH', sport, dport, length, checksum)
        return udp

    def _create_icmp_data(self, srcIp, srcPort, dstIp, dstPort):
        return self._create_tcp_data(srcIp, dstIp) + self._create_udp_data(srcPort, dstPort)

class WrongDigestException(Exception):
    pass

class Version107Client(CoAPAirClient):
    def __init__(self, host, port=5683, debug=False):
        super().__init__(host, port, debug)
        self.SECRET_KEY='JiangPan'
        self._sync()

    def __del__(self):
        self.client.stop()

    def _create_coap_client(self, host, port):
        return HelperClient(server=(host, port))
        
    def _sync(self):
        self.syncrequest = binascii.hexlify(os.urandom(4)).decode('utf8').upper()
        self.client_key = self.client.post("/sys/dev/sync", self.syncrequest).payload

    def _decrypt_payload(self, encrypted_payload):
        encoded_counter=encrypted_payload[0:8]
        aes=self._handle_AES(encoded_counter)
        encoded_message = encrypted_payload[8:-64].upper()
        digest=encrypted_payload[-64:]
        calculated_digest=self._create_digest(encoded_counter, encoded_message)
        if (digest != calculated_digest):
            raise WrongDigestException
        decoded_message = aes.decrypt(bytes.fromhex(encoded_message))
        unpaded_message = unpad(decoded_message, 16, style='pkcs7')
        return unpaded_message.decode('utf8')

    def _encrypt_payload(self, payload):
        self._update_client_key()  
        aes=self._handle_AES(self.client_key)
        paded_message = pad(bytes(payload.encode('utf8')), 16, style='pkcs7')
        encoded_message = aes.encrypt(paded_message).hex().upper()
        digest=self._create_digest(self.client_key, encoded_message)
        return self.client_key + encoded_message + digest

    def _create_digest(self, id, encoded_message):
        digest=hashlib.sha256(bytes((id + encoded_message).encode('utf8'))).hexdigest().upper()
        return digest

    def _update_client_key(self):
        self.client_key='{:x}'.format(int(self.client_key, 16)+1).upper()

    def _handle_AES(self, id):
        key_and_iv = hashlib.md5((self.SECRET_KEY + id).encode()).hexdigest().upper()
        half_keylen=len(key_and_iv) // 2
        secret_key = key_and_iv[0:half_keylen]
        iv = key_and_iv[half_keylen:]
        return AES.new(bytes(secret_key.encode('utf8')), AES.MODE_CBC, bytes(iv.encode('utf8')))

    def _get(self, param):
        path ="/sys/dev/status"
        decrypted_payload = None

        try:
            request = self.client.mk_request(defines.Codes.GET, path)
            request.observe = 0
            response = self.client.send_request(request, None, 2)
            encrypted_payload = response.payload
            decrypted_payload = self._decrypt_payload(encrypted_payload)
        except WrongDigestException:
            print("Message from device got corrupted")
        except Exception as e:
            print("Unexpected error:{}".format(e))

        if decrypted_payload is not None:
            return json.loads(decrypted_payload)["state"]["reported"]
        else:
            return {}

    def _set(self, key, value):
        path = "/sys/dev/control"
        try:
            payload = {"state":{"desired":{"CommandType":"app","DeviceId":"","EnduserId":"", key: value }}}
            encrypted_payload = self._encrypt_payload(json.dumps(payload))
            response = self.client.post(path, encrypted_payload)
            if (self.debug):
                print(response)
        except Exception as e:
            print("Unexpected error:{}".format(e))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--ipaddr', help='IP address of air purifier')
    parser.add_argument('--version', help='set the version of your device ', choices=['0.1.0','0.2.1', '1.0.7'], default='0.1.0')
    parser.add_argument('-d', '--debug', help='show debug output', action='store_true')
    parser.add_argument('--om', help='set fan speed', choices=['1','2','3','s','t'])
    parser.add_argument('--pwr', help='power on/off', choices=['0','1'])
    parser.add_argument('--mode', help='set mode', choices=['P','A','S','M','B','N'])
    parser.add_argument('--rhset', help='set target humidity', choices=['40','50','60','70'])
    parser.add_argument('--func', help='set function', choices=['P','PH'])
    parser.add_argument('--aqil', help='set light brightness', choices=['0','25','50','75','100'])
    parser.add_argument('--uil', help='set button lights on/off', choices=['0','1'])
    parser.add_argument('--ddp', help='set indicator pm2.5/IAI/Humidity', choices=['0','1','3'])
    parser.add_argument('--dt', help='set timer', choices=['0','1','2','3','4','5','6','7','8','9','10','11','12'])
    parser.add_argument('--cl', help='set child lock', choices=['True','False'])
    parser.add_argument('--wifi', help='read wifi options', action='store_true')
    parser.add_argument('--wifi-ssid', help='set wifi ssid')
    parser.add_argument('--wifi-pwd', help='set wifi password')
    parser.add_argument('--firmware', help='read firmware', action='store_true')
    parser.add_argument('--filters', help='read filters status', action='store_true')
    args = parser.parse_args()

    if args.ipaddr:
        devices = [ {'ip': args.ipaddr} ]
    else:
        if args.version in [ '0.2.1', '1.0.7']:
            print('Autodetection is not supported when using CoAP. Use --ipaddr to set an IP address.')
            sys.exit(1)

        devices = HTTPAirClient.ssdp(debug=args.debug)
        if not devices:
            print('Air purifier not autodetected. Try --ipaddr option to force specific IP address.')
            sys.exit(1)

    for device in devices:
        if args.version == '0.1.0':
            #c = HTTPAirClient(device['ip'], debug=args.debug)
            #c.load_key()
            pass
        elif args.version == '0.2.1':
            c = Version021Client(device['ip'], debug=args.debug)
        elif args.version == '1.0.7':
            c = Version107Client(device['ip'], debug=args.debug)

        if args.wifi:
            c.get_wifi()
            sys.exit(0)
        if args.firmware:
            c.get_firmware()
            sys.exit(0)
        if args.wifi_ssid or args.wifi_pwd:
            c.set_wifi(args.wifi_ssid, args.wifi_pwd)
            sys.exit(0)
        if args.filters:
            c.get_filters()
            sys.exit(0)

        values = {}
        if args.om:
            values['om'] = args.om
        if args.pwr:
            values['pwr'] = args.pwr
        if args.mode:
            values['mode'] = args.mode
        if args.rhset:
            values['rhset'] = int(args.rhset)
        if args.func:
            values['func'] = args.func
        if args.aqil:
            values['aqil'] = int(args.aqil)
        if args.ddp:
            values['ddp'] = args.ddp
        if args.uil:
            values['uil'] = args.uil
        if args.dt:
            values['dt'] = int(args.dt)
        if args.cl:
            values['cl'] = (args.cl == 'True')

        if values:
            c.set_values(values, debug=args.debug)
        else:
            c.get_status(debug=args.debug)


if __name__ == '__main__':
    main()
