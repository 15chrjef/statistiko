from merkato.merkato import Merkato
from merkato.utils.database_utils import get_first_price_after_time

def get_tuner_params_step():
    print('MUST BE A NUMBER')
    step = float(input("Step: "))
    return step


def get_tuner_params_spread():
    print('MUST BE A NUMBER')
    spread = float(input("spread: "))
    return spread


def get_tuner_params_quote():
    print('MUST BE A NUMBER')
    quote = float(input("quote: "))
    return quote


def get_tuner_params_base():
    print('MUST BE A NUMBER')
    base = float(input("base: "))
    return base

def get_tuner_distribution_strategy():
    print('Distribution Strategy?')
    print('for Aggressive -> 1')
    print('for neutral -> 2')
    print('for hyper-aggressive -> 3')
    strat = float(input('Selection: '))
    return strat


def start_tuner(step, spread, start_base, start_quote, distribution_strategy, start=0):
    config = generate_tuner_config(step, spread, start_base, start_quote, distribution_strategy, start)

    tuner = Merkato(**config)
    done = False
    while done == False:
        stuff = tuner.update()
        if stuff == "stuffs":
            # Get bprofit and qprofit and ending balances
            balances = tuner.exchange.get_balances()
            abs_b_profit = balances['base']['amount']['balance'] - start_base
            abs_q_profit = balances['coin']['amount']['balance'] - start_quote
            print("------------ qprofit: {} bprofit: {}".format(abs_q_profit, abs_b_profit))
            done = True
            return abs_q_profit, abs_b_profit
            
def generate_tuner_config(step, spread, start_base, start_quote, distribution_strategy, start):
    config = {}
    inner_config = {"limit_only": True}
    
    inner_config['exchange'] = 'test'
    inner_config['public_api_key'] = 1
    inner_config['private_api_key'] = 1
    inner_config['start'] = start

    config['configuration'] = inner_config
    config['base'] = 'BTC'
    config['coin'] = 'XMR'
    config['spread'] = spread
    config['starting_price'] = get_first_price_after_time(start)[0][3]
    config['ask_reserved_balance'] = start_quote
    config['bid_reserved_balance'] = start_base
    config['quote_volume'] = 0
    config['step'] = step
    config['base_volume'] = 0
    config['distribution_strategy'] = distribution_strategy

    return config
