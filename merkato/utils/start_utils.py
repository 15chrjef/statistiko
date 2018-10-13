from merkato.merkato import Merkato

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


def start_tuner(step, spread, start_base, start_quote, distribution_strategy, start, start_price, increased_orders):
    config = generate_tuner_config(step, spread, start_base, start_quote, distribution_strategy, start, start_price, increased_orders)

    tuner = Merkato(**config)
    done = False
    while done == False:
        stuff = tuner.update()
        if stuff == "stuffs":
            # Get bprofit and qprofit and ending balances
            balances = tuner.exchange.get_balances()
            abs_b_profit = balances['base']['amount']['balance'] - start_base
            abs_q_profit = balances['coin']['amount']['balance'] - start_quote
            
            print('volumes', tuner.base_volume, tuner.quote_volume)
            print("------------ qprofit: {} bprofit: {}".format(abs_q_profit, abs_b_profit))
            done = True
            return abs_q_profit, abs_b_profit
            
def generate_tuner_config(step, spread, start_base, start_quote, distribution_strategy, start, start_price, increased_orders):
    config = {}
    inner_config = {"limit_only": True}
    
    inner_config['exchange'] = 'test'
    inner_config['public_api_key'] = 1
    inner_config['private_api_key'] = 1
    inner_config['start'] = start
    inner_config['start_quote'] = start_quote
    inner_config['start_base'] = start_base

    config['configuration'] = inner_config
    config['base'] = 'BTC'
    config['coin'] = 'XMR'
    config['spread'] = spread
    config['starting_price'] = start_price
    config['ask_reserved_balance'] = start_quote
    config['bid_reserved_balance'] = start_base
    config['quote_volume'] = 0
    config['step'] = step
    config['base_volume'] = 0
    config['distribution_strategy'] = distribution_strategy
    config['increased_orders'] = increased_orders

    return config
