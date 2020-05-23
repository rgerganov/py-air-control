"""CoAP Air Client."""

# pylint: disable=invalid-name, missing-class-docstring, missing-function-docstring

import json
import logging
import os
import socket
import struct
import sys
import time

from coapthon import defines
from coapthon.client.helperclient import HelperClient
from coapthon.messages.request import Request
from coapthon.utils import generate_random_token


class NotSupportedException(Exception):
    pass


class CoAPAirClient:
    def __init__(self, host, port=5683):
        self.coapthon_logger = logging.getLogger("coapthon")
        self.coapthon_logger.setLevel("WARN")
        self.server = host
        self.port = port

    def _create_coap_client(self, host, port):
        return HelperClient(server=(host, port))

    def _send_over_socket(self, destination, packet):
        protocol = socket.getprotobyname("icmp")
        if os.geteuid() == 0:
            s = socket.socket(socket.AF_INET, socket.SOCK_RAW, protocol)
        else:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, protocol)
        try:
            s.sendto(packet, (destination, 0))
        except OSError:  # That fixes a mac os bug for me: OSError: [Errno 22] Invalid argument
            pass
        finally:
            s.close()

    def _get(self):
        path = "/sys/dev/status"
        try:
            client = self._create_coap_client(self.server, self.port)
            self._send_hello_sequence(client)
            request = client.mk_request(defines.Codes.GET, path)
            request.destination = server = (self.server, self.port)
            request.type = defines.Types["ACK"]
            request.token = generate_random_token(4)
            request.observe = 0
            response = client.send_request(request, None, 2)
        finally:
            client.stop()

        if response:
            return json.loads(response.payload)["state"]["reported"]
        else:
            return {}

    def _set(self, key, value):
        path = "/sys/dev/control"
        try:
            client = self._create_coap_client(self.server, self.port)
            self._send_hello_sequence(client)
            payload = {"state": {"desired": {key: value}}}
            client.post(path, json.dumps(payload))
        finally:
            client.stop()

    def _send_hello_sequence(self, client):
        ownIp = self._get_ip()

        header = self._create_icmp_header()
        data = self._create_icmp_data(ownIp, self.port, self.server, self.port)
        packet = header + data
        packet = self._create_icmp_header(self._checksum_icmp(packet)) + data

        self._send_over_socket(self.server, packet)

        # that is needed to give device time to open coap port, otherwise it may not respond properly
        time.sleep(0.5)

        request = Request()
        request.destination = server = (self.server, self.port)
        request.code = defines.Codes.EMPTY.number
        client.send_empty(request)

    def _get_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # doesn't even have to be reachable
            s.connect(("10.255.255.255", 1))
            ip = s.getsockname()[0]
        except:
            ip = "127.0.0.1"
        finally:
            s.close()
        return ip

    def _checksum_icmp(self, source_string):
        countTo = (int(len(source_string) / 2)) * 2
        sum = 0
        count = 0
        loByte = 0
        hiByte = 0
        while count < countTo:
            if sys.byteorder == "little":
                loByte = source_string[count]
                hiByte = source_string[count + 1]
            else:
                loByte = source_string[count + 1]
                hiByte = source_string[count]
            sum = sum + (hiByte * 256 + loByte)
            count += 2

        if countTo < len(source_string):  # Check for odd length
            loByte = source_string[len(source_string) - 1]
            sum += loByte

        sum &= 0xFFFFFFFF
        sum = (sum >> 16) + (sum & 0xFFFF)
        sum += sum >> 16
        answer = ~sum & 0xFFFF
        answer = socket.htons(answer)
        return answer

    def _create_icmp_header(self, checksum=0):
        ICMP_TYPE = 3
        ICMP_CODE = 3
        UNUSED = 0
        CHECKSUM = checksum
        header = struct.pack("!BBHI", ICMP_TYPE, ICMP_CODE, CHECKSUM, UNUSED)
        return header

    def _checksum_tcp(self, pkt):
        return 0  # looks like its irrelevant what we send here

    def _create_tcp_data(self, srcIp, dstIp, checksum=0):
        ip_version = 4
        ip_vhl = 5

        ip_ver = (ip_version << 4) + ip_vhl

        # Differentiate Service Field
        ip_dsc = 0
        ip_ecn = 0

        ip_dfc = (ip_dsc << 2) + ip_ecn

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
        tcp = struct.pack(
            "!BBHHHBBH4s4s",
            ip_ver,  # IP Version
            ip_dfc,  # Differentiate Service Feild
            ip_tol,  # Total Length
            ip_idf,  # Identification
            ip_flg,  # Flags
            ip_ttl,  # Time to leave
            ip_proto,  # protocol
            ip_chk,  # Checksum
            ip_saddr,  # Source IP
            ip_daddr,  # Destination IP
        )
        return tcp

    def _create_udp_data(self, srcPort, dstPort):
        sport = srcPort
        dport = dstPort
        length = 194
        checksum = 0
        udp = struct.pack("!HHHH", sport, dport, length, checksum)
        return udp

    def _create_icmp_data(self, srcIp, srcPort, dstIp, dstPort):
        return self._create_tcp_data(srcIp, dstIp) + self._create_udp_data(
            srcPort, dstPort
        )

    def set_values(self, values, debug=False):
        if debug:
            self.coapthon_logger.setLevel("DEBUG")
        for key in values:
            self._set(key, values[key])

    def get_status(self, debug=False):
        if debug:
            self.coapthon_logger.setLevel("DEBUG")
        status = self._get()
        return status

    def get_wifi(self):
        raise NotSupportedException

    def set_wifi(self, ssid, pwd):
        raise NotSupportedException

    def get_firmware(self):
        status = self._get()
        return status

    def get_filters(self):
        status = self._get()
        return status
