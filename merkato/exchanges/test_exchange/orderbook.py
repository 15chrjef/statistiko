import datetime
import time
from merkato.exchanges.test_exchange.constants import BID, ASK
from merkato.constants import BUY, SELL

class Orderbook:
    def __init__(self, bids=None, asks=None, start_base=0, start_quote=0):
        self.bids = bids if bids else []
        self.asks = asks if asks else []
        self.resolved = []
        self.bid_ticker = 'XMR'  # TODO: this needs to com from TestExchange
        self.ask_ticker = 'BTC'  # TODO: this needs to com from TestExchange
        self.current_order_id = 1
        self.base = start_base
        self.quote = start_quote

    def addBid(self, userID, amount, price):
        #is_market_order = price > self.asks[0].price
        # print('orerbook bid', amount, price )
        order = self.create_order(userID, amount, price, BUY)
        self.bids.append(order)
        self.bids = sorted(self.bids, key=lambda bid: bid["price"], reverse=True)
        return order['orderId']
        #if is_market_order:
        #    return self.resolve_market_order()
    
    def addAsk(self, userID, amount, price):
        # create ask
        # print('ask ', amount, price)
        order = self.create_order(userID, amount, price, SELL)
        # push ask
        self.asks.append(order)
        # sort asks
        self.asks = sorted(self.asks, key=lambda ask: ask["price"])
        return order['orderId']

    
    def get_order(self, order_id):
        for order in self.bids:
            if int(order['id']) == order_id:
                return order

        for order in self.asks:
            if int(order['id']) == order_id:
                return order

        for order in self.resolved:
            if int(order['id']) == order_id:
                return order


    def resolve_market_order(self, market_type, price):
        resolved_orders = []
        highest_bid = self.bids[0]
        lowest_ask = self.asks[0]

        if market_type == ASK:
            while float(lowest_ask["price"]) < price:
                old_ask = self.asks[0]
                self.asks.pop(0)
                self.add_resolved_order(lowest_ask, resolved_orders)
                lowest_ask = self.asks[0]
                self.base += old_ask['total'] * (1- old_ask['feepercent'])
                self.quote -= old_ask['amount']
        else:
            while float(highest_bid["price"]) > price:
                old_bid = self.bids[0]
                self.bids.pop(0)
                self.add_resolved_order(highest_bid, resolved_orders)
                highest_bid = self.bids[0]
                self.base -= old_bid['total'] 
                self.quote += old_bid['amount'] * (1- old_bid['feepercent'])

        return resolved_orders

    def generate_fake_orders(self, price):
        
        is_bid_market_order = price < self.bids[0]["price"]
        is_ask_market_order = price > self.asks[0]["price"]

        ###
        if(is_ask_market_order):
            return self.resolve_market_order(ASK, price)
        elif(is_bid_market_order):
            return self.resolve_market_order(BID, price)

    def add_resolved_order(self, order, resolved_orders):
        # resolved_amount = float(order["price"]) / float(order["amount"])
        # if order_type == BUY:
        #     amount = order["amount"] 
        # # else: amount = resolved_amount

        # new_order['amount'] = amount

        # new_order['total'] = float(order['price']) * float(amount)
    
        # self.current_order_id += 1
        order['date'] = datetime.datetime.now().isoformat(sep=" ")[:-7]
        order['time'] = int(time.time())
        resolved_orders.append(order)
        self.resolved.append(order)
    
    def create_order(self, user_id, amount, price, order_type):
        new_order =  {
            'fee': '0.00000000', 
            'feepercent': .001,
            "user_id": user_id,
            "price":price,
            'coin': self.bid_ticker,
            'market_pair': self.ask_ticker + '_' + self.bid_ticker,
            'id': self.current_order_id, 
            'orderId': self.current_order_id, 
            'market': 'BTC',
            'type': order_type
        }   

        new_order['amount'] = float(amount)
        new_order['initamount'] = amount

        new_order['total'] = float(price) * float(amount)
       
        self.current_order_id += 1

        return new_order
