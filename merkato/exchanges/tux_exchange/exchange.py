import hashlib
import hmac
import json
import requests
import time
import urllib.parse
import logging

from decimal import *
from merkato.exchanges.tux_exchange.utils import getQueryParameters, translate_ticker
from merkato.constants import MARKET
from merkato.exchanges.exchange_base import ExchangeBase
from merkato.constants import BUY, SELL

log = logging.getLogger(__name__)
getcontext().prec = 8


class TuxExchange(ExchangeBase):
    url = "https://tuxexchange.com/api"

    def __init__(self, config, coin, base):
        self.privatekey = config['private_api_key']
        self.publickey  = config['public_api_key']
        self.limit_only = config['limit_only']
        log.info('TuxExchange config', config)
        self.retries = 5
        self.coin = coin
        self.base = base
        self.ticker = translate_ticker(coin=coin, base=base)
        self.name = 'tux'


    def get_all_orders(self):
        ''' Returns all open orders for the ticker XYZ (not BTC_XYZ)
            :param coin: string
        '''
        # TODO: Accept BTC_XYZ by stripping BTC_ if it exists

        params = {"method": "getorders", "coin": self.coin}
        response = requests.get(self.url, params=params)

        response_json = json.loads(response.text)
        log.info(response.text)

        return response_json


    def get_my_open_orders(self, context_formatted=False):
        ''' Returns all open orders for the authenticated user '''

        query_parameters = { "method": "getmyopenorders" }

        orders = self._create_signed_request(query_parameters)
        if isinstance(orders, list):
            return {}
        filtered_orders = {order_id : order for order_id, order in orders.items() if self.ticker in order["market_pair"]}
        # Return orders in standardized format (list of buys/sells)
        # Tux returns {id: {order}, id: {order}, ...}, we want
        # [{order}, {order}, ...]
        return filtered_orders


    def cancel_order(self, order_id):
        ''' Cancels the order with the specified order ID
            :param order_id: string
        '''

        log.info("---> cancelling order")

        if order_id == 0:
            log.warning("Cancel order ID zero, bailing")

            return False

        query_parameters = {
            "method": "cancelorder",
            "market": self.base,
            "id": order_id
        }
        return self._create_signed_request(query_parameters)


    def get_ticker(self, coin=None):
        ''' Returns the current ticker data for the given coin. If no coin is given,
            it will return the ticker data for all coins.
            :param coin: string (of the format BTC_XYZ)
        '''

        params = { "method": "getticker" }
        response = requests.get(self.url, params=params)

        if not coin:
            return json.loads(response.text)

        response_json = json.loads(response.text)
        log.info(response_json[coin])

        return response_json[coin]


    def get_24h_volume(self, coin=None):
        ''' Returns the 24 hour volume for the given coin.
            If no coin is given, returns for all coins.
            :param coin string (of the form BTC_XYZ where XYZ is the alt ticker)
        '''

        params = { "method": "get24hvolume" }
        response = requests.get(self.url, params=params)

        if not coin:
            return json.loads(response.text)

        response_json = json.loads(response.text)
        log.info(response_json[coin])

        return response_json[coin]


    def get_balances(self):
        ''' Returns all balances on the exchange (not on the books)
        '''

        # also keys go unused, also coin...
        tuxParams = {"method" : "getmybalances"}

        response = self._create_signed_request(tuxParams)
        log.info(response)
        pair_balances = {"base" : {"amount": response[self.base],
                                   "name" : self.base},
                         "coin": {"amount": response[self.coin],
                                  "name": self.coin},
                        }

        return pair_balances


    def get_my_trade_history(self, start=0, end=0):
        ''' TODO Function Definition
        '''
        log.info("Getting trade history...")

        query_parameters = { "method": "getmytradehistory" }

        # if start != 0 and end != 0:
        #     query_parameters["start"] = str(start)
            
        # if start !=0 and end != 0:
        #     query_parameters["end"] = str(end)

        response = self._create_signed_request(query_parameters)
        accumulator = 0
        while len(response) > 0 and 'initamount' not in response[0]:
            accumulator += 1
            response = self._create_signed_request(query_parameters)
        print('accumulator', accumulator)
        filtered_history =  [trade for trade in response if self.ticker in trade["market_pair"]]
        return filtered_history


    def get_last_trade_price(self):
        ''' TODO Function Definition
        '''
        return self.get_ticker(self.ticker)["last"]


    def get_lowest_ask(self):
        ''' TODO Function Definition
        '''
        return self.get_ticker(self.ticker)["lowestAsk"]


    def get_highest_bid(self):
        ''' TODO Function Definition
        '''
        return self.get_ticker(self.ticker)["highestBid"]


    def get_partial_info(self, order_id):
        # Todo when tux implements the function
        order_info = self.get_my_order_info(order_id)
        return order_info[order_id]

    def get_my_order_info(self, order_id):
        query_parameters = { "method": "getmyorderinfo" }
        query_parameters.update({"orderid": order_id})
        response = self._create_signed_request(query_parameters)
        return response

    def get_total_amount(self, order_id):
        # Todo when tux implements the function
        pass


    def _create_signed_request(self, query_parameters, nonce=None, timeout=15):
        ''' Signs provided query parameters with API keys
            :param query_parameters: dictionary
            :param nonce: int
            :param timeout: int
        '''

        # return response needing signature, nonce created if not supplied
        if not nonce:
            nonce = int(time.time() * 1000)
        query_parameters.update({"nonce": nonce})
        post = urllib.parse.urlencode(query_parameters)
        signature = hmac.new(self.privatekey.encode('utf-8'), post.encode('utf-8'), hashlib.sha512).hexdigest()
        head = {'Key': self.publickey, 'Sign': signature}

        response = requests.post(self.url, data=query_parameters, headers=head, timeout=timeout).json()
        return response
