import csv
import datetime
import math
from math import floor
import os
import time
import logging

from decimal import *
from merkato.constants import BUY, SELL, ID, PRICE, LAST_ORDER, ASK_RESERVE, BID_RESERVE, EXCHANGE, ONE_BITCOIN, STARTING_PRICE, \
    ONE_SATOSHI, FIRST_ORDER, MARKET, TYPE, QUOTE_VOLUME, BASE_VOLUME
from merkato.utils.database_utils import update_merkato, insert_merkato, merkato_exists, kill_merkato
from merkato.utils import validate_merkato_initialization, get_relevant_exchange, \
    get_allocated_pair_balances, check_reserve_balances, get_last_order, get_new_history, \
    get_first_order, get_time_of_last_order, get_market_results, log_all_methods

log = logging.getLogger(__name__)
getcontext().prec = 8

@log_all_methods
class Merkato(object):
    def __init__(self, configuration, coin, base, spread,
                 bid_reserved_balance, ask_reserved_balance,
                 user_interface=None, profit_margin=0, first_order='', starting_price=.018, quote_volume=0, base_volume=0, step=1.0033, distribution_strategy=1):

        # validate_merkato_initialization(configuration, coin, base, spread)
        self.initialized = False
        UUID = configuration[EXCHANGE] + "coin={}_base={}".format(coin,base)
        self.mutex_UUID = UUID
        self.distribution_strategy = distribution_strategy
        self.spread = Decimal(spread)
        self.profit_margin = Decimal(profit_margin)
        self.starting_price = starting_price
        self.quote_volume = Decimal(quote_volume)
        self.base_volume = Decimal(base_volume)
        self.step = step
        self.first_order = ''
        self.last_order = ''
        # Exchanges have a maximum number of orders every user can place. Due
        # to this, every Merkato has a reserve of coins that are not currently
        # allocated. As the price approaches unallocated regions, the reserves
        # are deployed.
        self.bid_reserved_balance = Decimal(float(bid_reserved_balance))
        self.ask_reserved_balance = Decimal(float(ask_reserved_balance))

        # The current sum of all partially filled orders
        self.base_partials_balance = 0
        self.quote_partials_balance = 0

        self.user_interface = user_interface

        exchange_class = get_relevant_exchange(configuration[EXCHANGE])
        self.exchange = exchange_class(configuration, coin=coin, base=base)

        log.info("Creating New Merkato")

        total_pair_balances = self.exchange.get_balances()

        log.info("total pair balances: {}".format(total_pair_balances))

        history = self.exchange.get_my_trade_history()

        if len(history) > 0:
            log.debug('updating history first ID: {}'.format(history[0][ID]))
            new_last_order = history[0][ID]
            self.last_order = new_last_order
        self.distribute_initial_orders(total_base=bid_reserved_balance, total_alt=ask_reserved_balance)

        self.initialized = True  # to avoid being updated before orders placed


    def rebalance_orders(self, new_txes):

        factor = self.spread*self.profit_margin/2
        ordered_transactions = new_txes


        filled_orders = []
        market_orders = []
        
        if self.exchange.name != 'tux':
            self.exchange.process_new_transactions(ordered_transactions)

        for tx in ordered_transactions:
            orderid = tx['orderId']
            tx_id   = tx[ID]
            price   = tx[PRICE]

            filled_amount = Decimal(tx['amount'])
            init_amount   = Decimal(tx['initamount'])

            if self.exchange.name == 'tux':
                partial_fill_info = self.exchange.get_my_order_info(orderid)
                init_amount = partial_fill_info['initamount']
                partial_fill = (partial_fill_info['state'] == 'closed')
            else:
                partial_fill = self.exchange.is_partial_fill(orderid) # todo implement for tux (binance done)

            total_amount = self.get_total_amount(init_amount, orderid)
            amount = Decimal(total_amount)*Decimal((1-factor))

            if partial_fill:
                self.handle_partial_fill(tx[TYPE], filled_amount, tx_id)
                continue

            if orderid in filled_orders:
                self.handle_is_in_filled_orders(tx)
                continue

            if tx[TYPE] == SELL:
                buy_price = Decimal(price) * ( 1  - self.spread)

                market = self.exchange.buy(amount, buy_price)

                if market == MARKET:
                    market_orders.append((amount, buy_price, BUY, tx_id,))

                self.apply_filled_difference(tx, total_amount)

                is_round_trip = float(price) <= (float(self.starting_price) * float(1+(self.spread/2)))
                if is_round_trip:
                    self.base_volume += total_amount * Decimal(float(price))

            if tx[TYPE] == BUY:
                sell_price = Decimal(price) * ( 1  + self.spread)

                market = self.exchange.sell(amount, sell_price)
                
                if market == MARKET:
                    market_orders.append((amount, sell_price, SELL, tx_id))

                self.apply_filled_difference(tx, total_amount)

                is_round_trip = float(price) >= (float(self.starting_price) * float((1-(self.spread/2))))

                if is_round_trip:
                    self.quote_volume += total_amount

            if market != MARKET: 
                self.last_order = tx[ID]

            filled_orders.append(orderid)
            
            first_order = self.first_order
            no_first_order = first_order == ''

            if no_first_order:
                self.first_order = tx_id

        for order in market_orders:
            self.handle_market_order(*order)

        return ordered_transactions


    def apply_filled_difference(self, tx, total_amount):
        filled_difference = total_amount - Decimal(tx['amount'])
        tx_type = tx['type']
        if filled_difference > 0:
            if tx_type == SELL:
                self.base_partials_balance -= filled_difference * Decimal(tx[PRICE])
            if tx_type == BUY:
                self.quote_partials_balance -= filled_difference


    def decaying_bid_ladder(self, total_amount, step, start_price, hyper=False):
        '''total_amount is denominated in the base asset (BTC)
        '''
        # Abandon all hope, ye who enter here. This function uses black magic (math).

        scaling_factor = 0
        total_orders = floor(math.log(2, step)) if hyper == False else floor(math.log(2,step))/2# 277 for a step of 1.0025
        current_order = 0
        
        # Calculate scaling factor
        while current_order < total_orders:
            scaling_factor += Decimal(1/(step**current_order))
            current_order += 1

        current_order = 0
        amount = 0
        prior_reserve = self.bid_reserved_balance
        while current_order < total_orders:
            step_adjusted_factor = Decimal(step**current_order)
            current_bid_price = Decimal(start_price/step_adjusted_factor)
            if hyper == False:
                current_bid_total = Decimal(Decimal(total_amount)/(scaling_factor * step_adjusted_factor))
                current_bid_amount = Decimal(Decimal(total_amount)/(scaling_factor * step_adjusted_factor))/current_bid_price
            else:
                current_bid_total = Decimal(Decimal(total_amount)/(scaling_factor * step_adjusted_factor)) * 2
                current_bid_amount = Decimal(Decimal(total_amount)/(scaling_factor * step_adjusted_factor))/current_bid_price * 2
            amount += current_bid_amount
            
            # TODO Create lock
            response = self.exchange.buy(current_bid_amount, current_bid_price)

            self.remove_reserve(current_bid_total, BID_RESERVE) 
            # TODO Release lock
            
            current_order += 1
            self.avoid_blocking()


    def handle_is_in_filled_orders(self, tx):
        tx_type = tx[TYPE]
        filled_amount = Decimal(tx['amount'])
        price = Decimal(tx[PRICE])
        tx_id = tx[ID]
        if tx_type == BUY:
            self.quote_partials_balance += filled_amount
        if tx_type == SELL:
            self.base_partials_balance += filled_amount  * price
        self.last_order = tx_id


    def distribute_bids(self, price, total_to_distribute):
        # Allocates your market making balance on the bid side, in a way that
        # will never be completely exhausted (run out).
        # total_to_distribute is in the base currency (usually BTC)

        if self.distribution_strategy == 1:
            log.info('Distribute Agressive Bids')
            self.decaying_bid_ladder(Decimal(total_to_distribute), self.step, price)
        elif self.distribution_strategy == 2:
            log.info('Distribute Neutral Bids')
            self.decaying_bid_ladder(Decimal(total_to_distribute/(4/3)), self.step, price)
            self.decaying_bid_ladder(Decimal(total_to_distribute/4), self.step, price/2)
        elif self.distribution_strategy == 3:
            log.info('Distribute Hyper-Aggressive Asks')
            self.decaying_bid_ladder(Decimal(total_to_distribute), self.step, price, True)


    def get_total_amount(self, init_amount, orderid):
        if self.exchange.name == "tux":
            return Decimal(init_amount)

        else:
            return self.exchange.get_total_amount(orderid) # todo unimplemented on tux


    def decaying_ask_ladder(self, total_amount, step, start_price, hyper=False):
        # Places an ask ladder from the start_price to 2x the start_price.
        # The last order in the ladder is half the amount of the first
        # order in the ladder. The amount allocated at each step decays as
        # orders are placed.
        # Abandon all hope, ye who enter here. This function uses black magic (math).

        scaling_factor = 0
        total_orders = floor(math.log(2, step)) if hyper == False else floor(math.log(2, step))/2  # 277 for a step of 1.0025
        current_order = 0

        # Calculate scaling factor
        while current_order < total_orders:
            scaling_factor += Decimal(1/(step**current_order))
            current_order += 1

        current_order = 0
        amount = 0

        prior_reserve = self.ask_reserved_balance
        while current_order < total_orders:
            step_adjusted_factor = Decimal(step**current_order)
            current_ask_amount = total_amount/(scaling_factor * step_adjusted_factor) if hyper == False else total_amount/(scaling_factor * step_adjusted_factor) * 2
            current_ask_price = start_price*step_adjusted_factor
            amount += current_ask_amount

            # TODO Create lock
            response = self.exchange.sell(current_ask_amount, current_ask_price)

            # log.info('ask response {}'.format(response))

            self.remove_reserve(current_ask_amount, ASK_RESERVE) 
            # TODO Release lock

            current_order += 1
            self.avoid_blocking()

        # log.info('allocated amount: {}'.format(prior_reserve - self.ask_reserved_balance))


    def distribute_asks(self, price, total_to_distribute):
        # Allocates your market making balance on the ask side, in a way that
        # will never be completely exhausted (run out).
        if self.distribution_strategy == 1:
            log.info('Distribute Aggressive Asks')
            self.decaying_ask_ladder(Decimal(total_to_distribute), self.step, price)
        elif self.distribution_strategy == 2:
            log.info('Distribute Neutral Asks')
            self.decaying_ask_ladder(Decimal(total_to_distribute/(4/3)), self.step, price)
            self.decaying_ask_ladder(Decimal(total_to_distribute/4), self.step, price * 2)
        elif self.distribution_strategy == 3:
            log.info('Distribute Hyper-Aggressive Asks')
            self.decaying_ask_ladder(Decimal(total_to_distribute), self.step, price, True)


    def distribute_initial_orders(self, total_base, total_alt):
        ''' TODO: Function comment
        '''
        current_price = (Decimal(self.exchange.get_highest_bid()) + Decimal(self.exchange.get_lowest_ask()))/2
        if self.user_interface:
            current_price = Decimal(self.user_interface.confirm_price(current_price))
        # update_merkato(self.mutex_UUID, STARTING_PRICE, float(current_price))
        self.starting_price = float(current_price)

        ask_start = current_price + current_price*self.spread/2
        bid_start = current_price - current_price*self.spread/2
        
        self.distribute_bids(bid_start, total_base)
        self.distribute_asks(ask_start, total_alt)


    def handle_partial_fill(self, type, filled_qty, tx_id):
        # This was a buy, so we gained more of the quote asset. 
        # This was a partial fill, so the user's balance is increased by that amount. 
        # However, that amount is 'reserved' (will be placed on the books once the 
        # rest of the order is filled), and therefore is unavailable when creating new
        # Merkatos. Add this amount to a field 'quote_partials_balance'.
        # log.info('handle_partial_fill type {} filledqty {} tx_id {}'.format(type, filled_qty, tx_id))
        # update_merkato(self.mutex_UUID, LAST_ORDER, tx_id)
        self.last_order = tx_id
        if type == BUY:
            self.quote_partials_balance += filled_qty # may need a multiply by price
            # update_merkato(self.mutex_UUID, 'quote_partials_balance', float(self.quote_partials_balance))

        elif type == SELL:
            self.base_partials_balance += filled_qty
            # update_merkato(self.mutex_UUID, 'base_partials_balance', float(self.base_partials_balance))

        # 2. update the last order


    def handle_market_order(self, amount, price, type_to_place, tx_id):
        # log.info('handle market order price: {}, amount: {}, type_to_place: {}'.format(price, amount, type_to_place))
        
        last_id_before_market = self.last_order

        if type_to_place == BUY:
            self.exchange.market_buy(amount, price)

        elif type_to_place == SELL:
            self.exchange.market_sell(amount, price)        
                
        current_history = self.exchange.get_my_trade_history()
        if self.exchange.name != 'tux':
            self.exchange.process_new_transactions(current_history)
        market_history  = get_new_history(current_history, last_id_before_market)
        market_data     = get_market_results(market_history)


        # The sell gave us some BTC. The buy is executed with that BTC.
        # The market buy will get us X xmr in return. All of that xmr
        # should be placed at the original order's matching price.
        #
        # We need to do something here about the partials if it doesnt fully fill
        amount_executed = Decimal(market_data['amount_executed'])
        price_numerator = Decimal(market_data['price_numerator'])
        last_txid    = market_data['last_txid']
        self.last_order = last_txid

        market_order_filled = amount <= amount_executed
        if market_order_filled:
            if type_to_place == BUY:
                price = price * Decimal(1 + self.spread)
                self.exchange.sell(amount_executed, price) # Should never market order
            elif type_to_place == SELL:
                price = price * Decimal(1 - self.spread)
                self.exchange.buy(amount_executed, price)
        else:
            if type_to_place == BUY:
                self.quote_partials_balance += amount_executed
            else:
                self.base_partials_balance += amount_executed * price_numerator
        # A market buy occurred, so we need to update the db with the latest tx

    def get_context_history(self):
        now = str(datetime.datetime.now().isoformat()[:-7].replace("T", " "))
        last_trade_price = self.exchange.get_last_trade_price()
        current_history = self.exchange.get_my_trade_history()
        first_order = self.first_order
        new_history = get_new_history(current_history, first_order)

        self.exchange.process_new_transactions(new_history, context_only=True)

        context = {"price": (now, last_trade_price),
                "filled_orders": new_history,
                "open_orders": self.exchange.get_my_open_orders(context_formatted=True),
                "balances": self.exchange.get_balances(),
                "orderbook": self.exchange.get_all_orders(),
                "starting_price": self.starting_price,
                "starting_base": self.bid_reserved_balance * 4,
                "starting_quote": self.ask_reserved_balance * 4,
                "spread": self.spread,
                "step": self.step
                }
        
        return context


    def update(self):
        ''' TODO: Function comment
        '''
        # log.info("Update entered\n")
        
        now = str(datetime.datetime.now().isoformat()[:-7].replace("T", " "))
        last_trade_price = self.exchange.get_last_trade_price()
        if last_trade_price == "EOF":
            # Test merkato datastream ended
            print("test datastream ended")
            return "stuffs"

        first_order = self.first_order
        last_order = self.last_order
        
        current_history = self.exchange.get_my_trade_history()
        new_history = get_new_history(current_history, last_order)
        new_transactions = []
        
        if len(new_history) > 0:
            # log.info('we have new history')
            # log.debug("New transactions: {} \n".format(new_history))

            new_transactions = self.rebalance_orders(new_history)
            #self.merge_orders()
            # todo: Talk about whether merging 'close enough' orders is reasonable. 
            
        # context to be used for GUI plotting
        context = {"price": (now, last_trade_price),
                   "filled_orders": new_transactions,
                   "open_orders": self.exchange.get_my_open_orders(context_formatted=True),
                   "balances": self.exchange.get_balances(),
                   "orderbook": self.exchange.get_all_orders(),
                   "starting_price": self.starting_price,
                   "starting_base": self.bid_reserved_balance * 4,
                   "starting_quote": self.ask_reserved_balance * 4,
                   "spread": self.spread,
                   "step": self.step
                   }
        
        return context


    def modify_settings(self, settings):
        # replace old settings with new settings
        pass


    def add_reserve(self):
        ''' TODO: Function comment
            This will be necessary when we remove orders lower on the books so we can place more orders higher.
        '''
        pass


    def remove_reserve(self, amount, type_of_reserve):
        ''' TODO: Function comment
        '''
        current_reserve_amount = self.ask_reserved_balance if type_of_reserve == ASK_RESERVE else self.bid_reserved_balance
        invalid_reserve_reduction = amount > current_reserve_amount
        
        if invalid_reserve_reduction:
            return False
        if type_of_reserve == ASK_RESERVE:
            new_amount = self.ask_reserved_balance - amount
            self.ask_reserved_balance = new_amount           
        elif type_of_reserve == BID_RESERVE:
            new_amount = self.bid_reserved_balance - amount
            self.bid_reserved_balance = new_amount

        update_merkato(self.mutex_UUID, type_of_reserve, float(new_amount))
        return True


    def cancelrange(self, start, end):
        ''' TODO: Function comment
        '''
        open_orders = self.exchange.get_my_open_orders()
        for order in open_orders:
            price = open_orders[order][PRICE]
            order_id = open_orders[order][ID]
            if Decimal(price) >= Decimal(start) and Decimal(price) <= Decimal(end):
                self.exchange.cancel_order(order_id)

                log.debug("price: {}".format(price))

                # time.sleep(.3)


    def avoid_blocking(self):
        ''' TODO: Function comment
        '''
        if self.user_interface:

            try:
                self.user_interface.app.update_idletasks()
                self.user_interface.app.update()

            except UnicodeDecodeError:

                log.info("Caught Scroll Error")

            except:
                passS

    def check_balances_available(self, coin, amoount_to_add):
        total_pair_balances = self.exchange.get_balances()
        log.info("total pair balances: {}".format(total_pair_balances))
        allocated_pair_balances = get_allocated_pair_balances(self.exchange.name, self.exchange.base, self.exchange.coin)
        ask_reserved_balance = self.ask_reserved_balance if coin == 'BTC' else self.ask_reserved_balance + amoount_to_add
        bid_reserved_balance = self.bid_reserved_balance + amoount_to_add if coin == 'BTC' else self.bid_reserved_balance
        check_reserve_balances(total_pair_balances, allocated_pair_balances, coin_reserve=ask_reserved_balance, base_reserve=bid_reserved_balance)