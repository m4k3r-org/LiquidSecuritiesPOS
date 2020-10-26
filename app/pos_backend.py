#  _      _             _     _  _____                      _ _   _
# | |    (_)           (_)   | |/ ____|                    (_) | (_)
# | |     _  __ _ _   _ _  __| | (___   ___  ___ _   _ _ __ _| |_ _  ___  ___
# | |    | |/ _` | | | | |/ _` |\___ \ / _ \/ __| | | | '__| | __| |/ _ \/ __|
# | |____| | (_| | |_| | | (_| |____) |  __/ (__| |_| | |  | | |_| |  __/\__ \
# |______|_|\__, |\__,_|_|\__,_|_____/ \___|\___|\__,_|_|  |_|\__|_|\___||___/
#              | |
#              |_|    Demo Blockstream AMP POS
#
# This is an examples of POS terminal using GDK, python and M5Stack board.
#             DON'T USE THIS CODE IN PRODUCTION
#
# - http.server is not ready for a production service
# - we don't show how to add a tls certificate
# - configurations and mnemonic are saved in the same file in plain text
# - we use error messages in json without specific codes
# - connection status is not monitored
# - printer is not monitored
# - payments request are persisted in a local file
# - communication is not encrypted
# - messages are not signed
# - there is not an authentication phase


import http.server
import socketserver
import json
import datetime
import requests
import re
from greenaddress import init, Session
import pickle
import os.path
from escpos.printer import *

p = None # no printer
#p = Usb(0x0416,0x5011) # Bus 020 Device 004: ID 0416:5011 Winbond Electronics Corp. USB Thermal Printer
#p = Usb(0x0483,0x5743) # Bus 020 Device 004: ID 0483:5743 wide
#p = Serial(devfile=u'/dev/cu.ThermalPrinter-SPPDev') # Bluetooth

# Your green liquid mnemonic
GDK_MNEMONIC = ''

# Name of your Blockstream AMP subaccount in the wallet
GDK_SUBACCOUNT = 'Liquid Securities Account'

# Local name for your wallet
WALLET_NAME = 'wallet_1'

# List of allowed assets
ASSETS = [
    {'id':'6129504dafd3924f1cd18087da1e907e4d8813529b489d0883e82de79a6b0bad', 'name':'Pinot'},
]

init({})

class POSHandler(http.server.SimpleHTTPRequestHandler):
    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

    def do_HEAD(self):
        self._set_headers()

    # GET parse content and reply
    def do_GET(self):
        self._set_headers()
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # parse request
        request = {}
        path = self.path.split('?')
        request['path'] = path[0]
        request['args'] = {}
        if len(path)==2:
            args = path[1].split('&')
            for arg in args:
                element = arg.split('=')
                if len(element)==2:
                    request['args'][element[0]] = element[1]

        # return true
        if request['path'] == '/status':
            json_result = {'result': True, 'error': ''}
            self.wfile.write(json.dumps(json_result).encode())
            return

        # return accepted assets
        elif request['path'] == '/assets':
            json_result = {'result': ASSETS, 'error': ''}
            self.wfile.write(json.dumps(json_result).encode())
            return

        if subaccount == -1:
            json_result = {'result': False, 'error': 'Missing subaccount.'}
            self.wfile.write(json.dumps(json_result).encode())
            return

        # return gaid
        elif request['path'] == '/gaid':
            json_result = {'result': gaid, 'error': ''}

        # return owned asset ids or balance for a specified asset
        elif request['path'] == '/balance':
            balance = s.get_balance({'subaccount': subaccount, 'num_confs': 0}).resolve()
            if 'asset' in request['args']:
                json_result = {'result': {'asset': request['args']['asset'], 'amount': balance[request['args']['asset']]}, 'error': ''}
            else:
                json_result = {'result': list(balance.keys()), 'error': ''}

        # check if a payment is performed (passing pointer) or print all payment requests
        elif request['path'] == '/check':
            pointer = request['args'].get('pointer')
            if pointer is None:
                json_result = wallet['requests']
            else:
                json_result = []
                # fetch transaction from the wallet
                received_txs = []
                index = 0
                amount = 1
                while(True):
                    transactions = s.get_transactions({'subaccount': subaccount,'first': index, 'count':amount}).resolve()
                    for transaction in transactions['transactions']:
                        if transaction['type']=='incoming':
                            outputs = []
                            for output in transaction['outputs']:
                                if not 'asset_id' in output:
                                    output['asset_id'] = '???'
                                if not 'satoshi' in output:
                                    output['satoshi'] = 0
                                if output['pointer'] != 0:
                                    outputs.append({'asset_id': output['asset_id'], 'satoshi': output['satoshi'], 'pointer': output['pointer']})
                            received_txs.append({'txhash': transaction['txhash'], 'outputs': outputs})
                    if len(transactions['transactions']) < amount:
                        break
                    index = index + 1

                # match transaction on local database
                found = False
                for request in wallet['requests']:
                    if request['pointer'] == int(pointer):
                        asset = request['asset']
                        amount = request['amount']
                        time = request['time']
                        found = True
                        break

                # summarized received transaction (using GDK services)
                if found:
                    transactions = {}
                    moved_assets = {}
                    for tx in received_txs:
                        for output in tx['outputs']:
                            if output['pointer'] == int(pointer):
                                if tx['txhash'] not in transactions:
                                    transactions[tx['txhash']] = {}
                                if output['asset_id'] not in transactions[tx['txhash']]:
                                    transactions[tx['txhash']][output['asset_id']] = output['satoshi']
                                else:
                                    transactions[tx['txhash']][output['asset_id']] = transactions[tx['txhash']][output['asset_id']] + output['satoshi']

                                if output['asset_id'] not in moved_assets:
                                    moved_assets[output['asset_id']] = output['satoshi']
                                else:
                                    moved_assets[output['asset_id']] = moved_assets[output['asset_id']] + output['satoshi']

                    print(transactions)
                    print(moved_assets)

                    # check if the payment is completed, partial or we are still waiting for it
                    paid = False
                    fully_paid = False
                    if asset in moved_assets:
                        paid = True
                        if not moved_assets[asset] < int(amount):
                            fully_paid = True
                            for request in wallet['requests']:
                                if request['pointer'] == pointer:
                                    request['paid'] = True
                            with open(f'{WALLET_NAME}.pickle', 'wb') as f:
                                pickle.dump(wallet, f)

                    # print
                    if paid:
                        try:
                            if p:
                                p.set(align='center', width=2, height=2)
                                p.image('./logo.png')
                                p.text('Blockstream AMP POS')
                                p.text('\n')
                                p.text('\n')
                                p.text('\n')
                                for txid in transactions.keys():
                                    p.set(align='left', width=1, height=1)
                                    p.text('Received Liquid assets:')
                                    p.text('\n')

                                    for assetid in transactions[txid].keys():
                                        p.text(f'{transactions[txid][assetid]} sats - asset {assetid}')
                                        p.text('\n')
                                        p.text('\n')

                                    p.text('\n')
                                    p.text(f'Transaction: {txid}')
                                    p.text('\n')
                                    p.set(align='center')
                                    p.qr(f'https://blockstream.info/liquid/tx/{txid}', size=6)
                                    p.text('\n')
                                p.set(align='right')
                                p.text(timestamp)
                                p.text('\n')
                                p.text('\n')
                                p.set(align='center')
                                p.text('github.com/valerio-vaccaro/LiquidSecuritiesPOS')
                                p.cut()
                        except:
                            print('print error')

                    if paid:
                        if fully_paid:
                            json_result = {'result': 'PAYED', 'error': ''}
                        else:
                            json_result = {'result': 'PARTIALLY PAYED', 'error': ''}
                    else:
                        json_result = {'result': 'NOT PAYED', 'error': ''}
                else:
                    json_result = {'result': 'NOT FOUND', 'error': ''}


        # get an address from GDK and save relevant information locally (name, asset, amount)
        elif request['path'] == '/address':
            name = request['args'].get('name')
            asset = request['args'].get('asset')
            amount = request['args'].get('amount')
            address = s.get_receive_address({'subaccount': subaccount}).resolve()
            json_result = {'result': {'address': address['address'], 'pointer': address['pointer']}, 'error': ''}
            wallet['requests'].append({'name': name, 'time': timestamp, 'address': address['address'], 'pointer': address['pointer'], 'asset': asset, 'amount': amount, 'paid': False})
            with open(f'{WALLET_NAME}.pickle', 'wb') as f:
                pickle.dump(wallet, f)

        # print a summary about payment requests saved locally
        elif request['path'] == '/summary':
            try:
                if p:
                    p.set(align='center', width=2, height=2)
                    p.image('./logo.png')
                    p.text('BLOCKSTREAM AMP POS\n')
                    p.text('Requests\n\n\n')
                    for request in wallet['requests']:
                        name = request['name']
                        time = request['time']
                        address = request['address']
                        pointer = request['pointer']
                        asset = request['asset']
                        amount = request['amount']
                        paid = request['paid']
                        p.set(align='left', width=1, height=1)
                        p.text(f'Name: {name}\n')
                        p.text(f'Time: {time}\n')
                        p.text(f'Pointer: {pointer}\n')
                        p.text(f'Asset: {asset}\n')
                        p.text(f'Amount: {amount}\n')
                        p.text(f'Paid: {paid}\n')
                        p.text(f'Address:\n')
                        p.set(align='center')
                        p.qr(address, size=6)
                        p.text('\n\n')
                    p.set(align='right')
                    p.text(timestamp)
                    p.text('\n\n')
                    p.set(align='center')
                    p.text('github.com/valerio-vaccaro/LiquidSecuritiesPOS')
                    p.cut()
            except:
                print('print error')
            json_result = {'result': 'ok', 'error': ''}
        else:
            json_result = {'result': False, 'error': 'Wrong URI called.'}

        # write results
        #s.disconnect()
        self.wfile.write(json.dumps(json_result).encode())


def run(server_class=socketserver.TCPServer, handler_class=POSHandler, port=8008):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    httpd.allow_reuse_address = True

    print ('Starting POS backend on port {} ...'.format(port))
    httpd.serve_forever()


if __name__ == "__main__":
    print(
        '  _      _             _     _  _____                      _ _   _\n' +
        ' | |    (_)           (_)   | |/ ____|                    (_) | (_)\n' +
        ' | |     _  __ _ _   _ _  __| | (___   ___  ___ _   _ _ __ _| |_ _  ___  ___\n' +
        ' | |    | |/ _` | | | | |/ _` |\\___ \\ / _ \\/ __| | | | \'__| | __| |/ _ \\/ __|\n' +
        ' | |____| | (_| | |_| | | (_| |____) |  __/ (__| |_| | |  | | |_| |  __/\\__ \\\n' +
        ' |______|_|\\__, |\\__,_|_|\\__,_|_____/ \\___|\\___|\\__,_|_|  |_|\\__|_|\\___||___/\n' +
        '              | |\n'
        '              |_|    Demo Blockstream AMP POS\n\n' +
        ' This is an examples of POS terminal using GDK, python and M5Stack board.\n' +
        '            DON\'T USE THIS CODE IN PRODUCTION\n'
    )
    from sys import argv

    wallet = {}
    wallet['requests'] = []

    if os.path.isfile(f'{WALLET_NAME}.pickle'):
        with open(f'{WALLET_NAME}.pickle', 'rb') as f:
            wallet = pickle.load(f)
            print(f'Wallet {WALLET_NAME}.pickle found!')
            print(wallet)
    else:
        with open(f'{WALLET_NAME}.pickle', 'wb') as f:
            pickle.dump(wallet, f)
            print(f'Wallet {WALLET_NAME}.pickle not found! Generating a new one')

    # connect to green serivicies
    s = Session({"name":"liquid", "log_level":"info"})
    s.login({}, GDK_MNEMONIC).resolve()
    s.change_settings({"unit":"sats"}).resolve()

    # check for the right subaccount
    subaccount = -1
    subaccounts = s.get_subaccounts().resolve()
    for sub in subaccounts['subaccounts']:
        if sub['name'] == GDK_SUBACCOUNT:
            if sub['type'] != '2of2_no_recovery':
                json_result = {'result': False, 'error': 'Missing subaccount.'}
                self.wfile.write(json.dumps(json_result).encode())
                exit(1)
            subaccount = sub['pointer']
            gaid = sub['receiving_id']
            break

    if len(argv) == 2:
        run(port=int(argv[1]))
    else:
        run()

    s.disconnect()
