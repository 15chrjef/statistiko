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
    print('for neautral -> 2')
    print('for hyper-aggressive -> 3')
    strat = float(input('Selection: '))
    return strat


def start_tuner(step, spread, start_base, start_quote, distribution_strategy):
    config = generate_tuner_config(step, spread, start_base, start_quote, distribution_strategy)

    tuner = Merkato(**config)
    done = False
    while done == False:
        stuff = tuner.update()
        if stuff == "stuffs":
            # Get bprofit and qprofit and ending balances
            quote_volume = float(tuner.quote_volume)
            base_volume = float(tuner.base_volume)
            spread = tuner.spread
            q_profit = quote_volume * (float(spread) - .002)
            b_profit = base_volume * (float(spread) - .002)
            print("------------ qprofit: {} bprofit: {}".format(q_profit, b_profit))
            done = True
            return q_profit, b_profit
            
def generate_tuner_config(step, spread, start_base, start_quote, distribution_strategy):
    config = {}
    inner_config = {"limit_only": True}
    
    inner_config['exchange'] = 'test'
    inner_config['public_api_key'] = 1
    inner_config['private_api_key'] = 1

    config['configuration'] = inner_config
    config['base'] = 'BTC'
    config['coin'] = 'XMR'
    config['spread'] = spread
    config['starting_price'] = 0.0157
    config['ask_reserved_balance'] = start_quote
    config['bid_reserved_balance'] = start_base
    config['quote_volume'] = 0
    config['step'] = step
    config['base_volume'] = 0
    config['distribution_strategy'] = distribution_strategy

    return config
