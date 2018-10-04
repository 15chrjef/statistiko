from merkato.exchanges.test_exchange.constants import test_asks, test_bids

DEBUG = True

def apply_resolved_orders(current_accounts, resolved_orders):
    # if resolved_orders:
    #     if DEBUG:
    #         print("-----------------------")
    #         print("current accounts:\n\n",current_accounts)
    #         print("-----------------------")
    #         print("resolved orders:\n\n",resolved_orders)
    #         print("-----------------------")
    for user_id, user in resolved_orders.items():
        #user_id = user["user_id"]
        user_is_not_in_accounts = user_id not in current_accounts
        if user_is_not_in_accounts:
            current_accounts[user_id] = {}
        for ticker, amount in user.items():
            user_does_not_have_ticker = ticker not in  current_accounts[user_id]
            if user_does_not_have_ticker:
                user[ticker] = resolved_orders[user_id][ticker]
            else:
                user[ticker] += resolved_orders[user_id][ticker]

def get_initial_orderbook(start):
    config = {}
    test_asks[0]['price'] = float(start) + .0001
    test_bids[0]['price'] = float(start) - .0001
    config['asks'] = test_asks
    config['bids'] = test_bids
    return config