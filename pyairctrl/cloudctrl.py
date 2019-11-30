#!/usr/bin/env python3
import os
import re
import json
import email
import struct
import base64
import hashlib
import binascii
import argparse
import configparser
import urllib.request
import urllib.parse
from pyairctrl.airctrl import AirClient

def parse_attr(str, key):
    p = re.compile('%s=\"(.+?)\"' % key)
    m = p.search(str)
    return m.group(1)


class CloudClient(object):

    def __init__(self, device_id, debug=False):
        self._device_id = device_id
        self._debug = debug

    def _login(self):
        print('Logging in with {}'.format(self._client_id))
        url = 'https://www.ecdinterface.philips.com/DevicePortalICPRequestHandler/RequestHandler.ashx'
        auth = 'CBAuth Type="TLS", Client="%s", Authentication="%s"' % (self._client_id, self._client_key)
        req_body = {'correlationId': 1}
        req_body['clientHeaders'] = {'clientId': self._client_id,
                                     'deviceType': 'FI-AIR_KPSPROV',
                                     'country': 'US',
                                     'language': 'en',
                                     'components': [{'id': 'FI-AIR-AND', 'version': 64}],
                                     'icpVersion': 'CPPDC_8.2.4_B.2'}
        req_body['body'] = [{'action': {'name': 'PortalLocationRequest', 'version': 1},
                             'requestNr': 1,
                             'errorCode': 0,
                             'content': {'type': 0, 'data': '{\"pageSize\":4}'},
                             'attachResponse': True}]

        req = urllib.request.Request(url=url, data=json.dumps(req_body).encode('ascii'), method='POST')
        req.add_header('Authorization', auth)
        req.add_header('Content-Type', 'application/CB-Message; encoding=JSON')
        with urllib.request.urlopen(req) as response:
            www_auth = response.getheader('WWW-Authenticate')
            if self._debug:
                print(www_auth)
            self._sso_key = parse_attr(www_auth, "SSOKey")
            self._sso_token = parse_attr(www_auth, "SSOToken")
            self._nonce = parse_attr(www_auth, "Nonce")

    def _create_auth(self, url):
        num = 1
        host = urllib.parse.urlparse(url).hostname
        m = hashlib.sha1()
        m.update(b'\x05')
        m.update(self._client_id.encode('ascii'))
        m.update(host.encode('ascii'))
        m.update(base64.b64decode(self._sso_key))
        m.update(struct.pack('<I', num))
        m.update(base64.b64decode(self._nonce))
        key = m.digest()[:16]
        auth0 = base64.b64encode(key).decode('ascii')
        return 'CBAuth Type="SSO", Client="%s", RequestNr="%d", Nonce="%s", SSOToken="%s", Authentication="%s"' % (self._client_id, num, self._nonce, self._sso_token, auth0)

    def _create_account(self):
        print('Creating cloud account ...')
        # hardcoded credentials for account provisioning
        self._client_id = '000000fff0000019'
        self._client_key = 'QR3FiHoEQcSZ9S5XxsZwXQ=='
        self._login()

        url = 'https://kps.dc1.philips.com/KpsRequestHandler/index.ashx'
        auth = self._create_auth(url)

        rand_id = binascii.hexlify(os.urandom(15)).decode('ascii')
        body_data = {'Device': {'Type': 'fira', 'Version': '6.0.1_24', 'Id': rand_id},
                     'Application': {'Type': 'FI-AIR-AND', 'Version': 'com.xakcop.air', 'Id': '64'}}
        req_body = {'correlationId': 1}
        req_body['clientHeaders'] = {'clientId': self._client_id,
                                     'deviceType': 'FI-AIR_KPSPROV',
                                     'country': 'US',
                                     'language': 'en',
                                     'components': [{'id': 'FI-AIR-AND', 'version': 64}],
                                     'icpVersion': 'CPPDC_8.2.4_B.2'}
        req_body['body'] = [{'action': {'name': 'ProvisionRequest', 'version': 1},
                             'requestNr': 1,
                             'errorCode': 0,
                             'content': {'type': 0, 'data': json.dumps(body_data)},
                             'attachResponse': True}]

        req = urllib.request.Request(url=url, data=json.dumps(req_body).encode('ascii'), method='POST')
        req.add_header('Authorization', auth)
        req.add_header('Content-Type', 'application/CB-Message; encoding=JSON')
        with urllib.request.urlopen(req) as response:
            content_type = response.getheader('Content-Type')
            body = response.read().decode('ascii')
            parts = "Content-Type: %s\n\n%s" % (content_type, body)

        if self._debug:
            print(parts)
        msg = email.message_from_string(parts)
        if not msg.is_multipart():
            raise Exception('Expected multipart response')
        for part in msg.get_payload():
            if part.get_content_type() == 'application/cb-message':
                continue
            p = json.loads(part.get_payload(decode=False))
            client_id, client_key = p['ClientId'], p['Key']
            bytes_key = bytes.fromhex(client_key)
            client_key = base64.b64encode(bytes_key).decode('ascii')

        print('Client id: {}'.format(client_id))
        print('Client key: {}'.format(client_key))
        config = configparser.ConfigParser()
        fpath = os.path.expanduser('~/.pyairctrl')
        config.read(fpath)
        if 'cloud' not in config.sections():
            config['cloud'] = {}
        config['cloud']['client_id'] = client_id
        config['cloud']['client_key'] = client_key
        self._client_id = client_id
        self._client_key = client_key
        with open(fpath, 'w') as f:
            config.write(f)

    def load_credentials(self):
        fpath = os.path.expanduser('~/.pyairctrl')
        if os.path.isfile(fpath):
            config = configparser.ConfigParser()
            config.read(fpath)
            if 'cloud' in config and 'client_id' in config['cloud']:
                self._client_id = config['cloud']['client_id']
                self._client_key = config['cloud']['client_key']
            else:
                self._create_account()
        else:
            self._create_account()

    def _multi_part(self, part1, part2):
        part1_str = json.dumps(part1).replace(' ', '')
        part2_str = json.dumps(part2).replace(' ', '')
        result = "--ICPMimeBoundary\r\n"
        result += "Content-Type: application/CB-Message; encoding=JSON\r\n"
        result += "Content-Length: " + str(len(part1_str)).zfill(10) + "\r\n\r\n"
        result += part1_str + "\r\n\r\n"
        result += "--ICPMimeBoundary\r\n"
        result += "Content-Type: application/octet-stream\r\n"
        result += "Content-Length: " + str(len(part2_str)).zfill(10) + "\r\n\r\n"
        result += part2_str + "\r\n\r\n"
        result += "--ICPMimeBoundary--"
        return result.encode('ascii')

    def set_values(self, values):
        self._login()

        print('Sending event {} to device with id {}'.format(str(values), self._device_id))

        url = 'https://ep.dcs.dc1.philips.com/DCS.EventPublisherService/Services/External/json'
        auth = self._create_auth(url)

        part1 = {}
        part1['correlationId'] = 14
        part1['clientHeaders'] = {'clientId': self._client_id,
                                  'deviceType': 'FI-AIR-AND',
                                  'country': 'US',
                                  'language': 'en',
                                  'components': [{'id': 'FI-AIR-AND', 'version': 64}]}
        part1['body'] = [{'action': {'name': 'PublishEventRequest', 'version': 1},
                          'requestNr': 1,
                          'errorcode': 0,
                          'content': {'type': 1, 'attachment': {}},
                          'attachResponse': True}]

        part2_data = {'product': '1',
                      'port': 'air',
                      'data': values}
        part2 = {}
        part2['event'] = {'eventType': 'DICOMM-REQUEST',
                          'priority': 20,
                          'replyTo': self._client_id,
                          'conversationId': '',
                          'serviceTag': '',
                          'data': json.dumps(part2_data),
                          'action': 'PUTPROPS'}
        part2['targets'] = [self._device_id]
        part2['ttl'] = 5

        req_body = self._multi_part(part1, part2)

        req = urllib.request.Request(url=url, data=req_body, method='POST')
        req.add_header('Authorization', auth)
        req.add_header('Content-Type', 'multipart/mixed; boundary="ICPMimeBoundary"')
        with urllib.request.urlopen(req) as response:
            resp = response.read().decode('ascii')
            if self._debug:
                print(resp)

    def pair(self, ip_addr):
        cc = AirClient(ip_addr)
        cc.load_key()
        print('Pairing with {} ...'.format(ip_addr))
        pair_secret = 'ad388b4036986421'
        cc.pair(self._client_id, pair_secret)

        self._login()
        print('Sending pair request to cloud service ...')

        url = 'http://ps.dc1.philips.com/PSRequestHandler/index.ashx'
        auth = self._create_auth(url)

        part1 = {}
        part1['correlationId'] = 15
        part1['clientHeaders'] = {'clientId': self._client_id,
                                  'deviceType': 'FI-AIR-AND',
                                  'country': 'US',
                                  'language': 'en',
                                  'components': [{'id': 'FI-AIR-AND', 'version': 64}]}
        part1['body'] = [{'action': {'name': 'AddRelationshipRequest', 'version': 1},
                          'requestNr': 1,
                          'errorcode': 0,
                          'content': {'type': 1, 'attachment': {}},
                          'attachResponse': True}]

        part2 = {}
        part2['Trustor'] = {'Provider': 'cpp', 'ID': self._client_id, 'Type': 'FI-AIR-AND'}
        part2['Trustee'] = {'Provider': 'cpp', 'ID': self._device_id, 'Type': 'AirPurifier'}
        part2['PairingData'] = {'Secret': pair_secret, 'MatchIPAddress': False, 'RequestTtl': 5}
        part2['Relationship'] = {'Type': 'di-comm', 'Permissions': ['Response', 'Change'], 'AllowDelegation': False, 'Metadata': '', 'Ttl': 1000000000}

        req_body = self._multi_part(part1, part2)
        if self._debug:
            print(req_body)

        req = urllib.request.Request(url=url, data=req_body, method='POST')
        req.add_header('Authorization', auth)
        req.add_header('Content-Type', 'multipart/mixed; boundary="ICPMimeBoundary"')
        with urllib.request.urlopen(req) as response:
            content_type = response.getheader('Content-Type')
            body = response.read().decode('ascii')
            parts = "Content-Type: %s\n\n%s" % (content_type, body)

        if self._debug:
            print(parts)
        msg = email.message_from_string(parts)
        if not msg.is_multipart():
            raise Exception('Expected multipart response')
        for part in msg.get_payload():
            if part.get_content_type() == 'application/cb-message':
                continue
            p = json.loads(part.get_payload(decode=False))
            rel_status = p['RelationshipStatus']
            print('Relationship status: {}'.format(rel_status))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('device_id', help='Purifier device ID')
    parser.add_argument('-d', '--debug', help='show debug output', action='store_true')
    parser.add_argument('--om', help='set fan speed', choices=['1','2','3','s','t'])
    parser.add_argument('--pwr', help='power on/off', choices=['0','1'])
    parser.add_argument('--mode', help='set mode', choices=['P','A','S','M','B','N'])
    parser.add_argument('--rhset', help='set target humidity', choices=['40','50','60','70'])
    parser.add_argument('--func', help='set function', choices=['P','PH'])
    parser.add_argument('--aqil', help='set light brightness', choices=['0','25','50','75','100'])
    parser.add_argument('--uil', help='set button lights on/off', choices=['0','1'])
    parser.add_argument('--ddp', help='set indicator pm2.5/IAI', choices=['0','1'])
    parser.add_argument('--dt', help='set timer', choices=['0','1','2','3','4','5'])
    parser.add_argument('--pair', help='pair with the device having the given IP')
    args = parser.parse_args()

    c = CloudClient(args.device_id, args.debug)
    c.load_credentials()
    if args.pair:
        c.pair(args.pair)

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

    if values:
        c.set_values(values)

if __name__ == '__main__':
    main()
