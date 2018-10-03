from merkato.merkato_config import load_config, get_config, create_config
from merkato.parser import parse
from merkato.utils.database_utils import no_merkatos_table_exists, create_merkatos_table, insert_merkato, get_all_merkatos, get_exchange, no_exchanges_table_exists, create_exchanges_table, insert_price_data, drop_merkatos_table, drop_exchanges_table, insert_exchange, get_all_exchanges, no_price_data_table_exists, create_price_data_table
from merkato.utils import generate_complete_merkato_configs, ensure_bytes, encrypt, decrypt, get_relevant_exchange
from merkato.utils.start_utils import get_tuner_params_spread, get_tuner_params_step, get_tuner_params_base, get_tuner_params_quote, start_tuner, get_tuner_distribution_strategy
from merkato.exchanges.tux_exchange.utils import validate_credentials
from merkato.exchanges.binance_exchange.utils import validate_keys
from merkato.exchanges.kraken_exchange.utils import validate_kraken


import getpass
import sqlite3
import time
import pprint
import datetime
import tkinter as tk
import json

# Yes, I know we need to abstract these out later. This is me hacking.
def encrypt_keys(config, password=None):
    ''' Encrypts the API keys before storing the config in the database
    '''
    public_key  = config["public_api_key"]
    private_key = config["private_api_key"]

    if password is None:
        password = getpass.getpass("\n\ndatabase password:") # Prompt user for password / get password from Nasa. This should be a popup?

    password, public_key, private_key = ensure_bytes(password, public_key, private_key)

    # encrypt(password, data)
    # Inputs are of type:
    # - password: bytes
    # - data:     bytes

    public_key_encrypted  = encrypt(password, public_key)
    private_key_encrypted = encrypt(password, private_key)
    config["public_api_key"]  = public_key_encrypted
    config["private_api_key"] = private_key_encrypted
    return config


def decrypt_keys(config, password=None):
    ''' Decrypts the API keys before storing the config in the database
    '''
    public_key  = config["public_api_key"]
    private_key = config["private_api_key"]

    if password is None:
        password = getpass.getpass("\n\ndatabase password:") # Prompt user for password / get password from Nasa. This should be a popup?

    password, public_key, private_key = ensure_bytes(password, public_key, private_key)

    # decrypt(password, data)
    # Inputs are of type:
    # - password: bytes
    # - data:     bytes

    public_key_decrypted  = decrypt(password, public_key)
    private_key_decrypted = decrypt(password, private_key)
    config["public_api_key"]  = public_key_decrypted.decode('utf-8')
    config["private_api_key"] = private_key_decrypted.decode('utf-8')

    return config


def insert_config_into_exchanges(config):
    limit_only = config["limit_only"]
    public_key = config["public_api_key"]
    private_key = config["private_api_key"]
    exchange = config["exchange"]

    if no_exchanges_table_exists():
        create_exchanges_table()
    insert_exchange(exchange, public_key, private_key, limit_only)


welcome_txt = """Welcome to Statistiko Would you like to run current statistiko, or add a new exchange?."""
exchange_added_text = "The Exchange has been added, would you like to run current statistikos, or add another exchange?"
drop_merkatos_txt = "Do you want to drop statistikos?"
drop_exchanges_txt = "Do you want to drop exchanges?"
public_key_text = """Please enter your api public key"""
private_key_text = """Please enter your api secret key"""
exchange_select_txt = """Please select an exchange"""


class Application(tk.Frame):
    def __init__(self):
        self.base = "BTC"
        self.coin = "XMR"
        self.spread = .02
        self.coin_reserve = 17
        self.base_reserve = .4
        self.create_widgets()


    def create_widgets(self, message=None):
        if message == None:
            message = welcome_txt

        print(message)
        print('Run Statistikos -> 1')
        print('Add Statistiko -> 2')
        print('Add Exchange -> 3')
        print('Run Tuner -> 4')
        print('Run All Tuners -> 5')
        print('Drop Tables -> 6')
        print('Quit -> 7')
        selection = input('Selection: ')
        self.handle_welcome_selection(selection)


    def handle_welcome_selection(self, selection):
        if selection == '1':
            self.start_statistikos()
        elif selection == '2':
            self.add_statistiko()
        elif selection == '3':
            self.add_exchange()
        elif selection == '4':
            self.handle_start_tuner()
            return
        elif selection == '5':
            self.handle_start_all_tuners()
            return
        elif selection == '6':
            self.drop_tables()
            return
        else:
            return

    def drop_tables(self):
        drop_merkatos_table()
        drop_exchanges_table()
        create_merkatos_table()
        create_exchanges_table()

    def handle_start_all_tuners(self):
        base = 10
        quote = 636
        distribution_strategy = get_tuner_distribution_strategy()
        results = []
        print("test")
        for step_mult in range(0,20):
            step = 1.01 + .005*step_mult

            for spread_mult in range(0,30):
                spread = .05+spread_mult*.005
                (q_profit, b_profit) = start_tuner(step, spread, base, quote, distribution_strategy)
                result = [str(step), str(spread), q_profit, b_profit]
                results.append(result)
                print("("+str(result[0])+","+str(result[1])+","+str(result[2])+","+str(result[3])+")")

        print("Format: (step, spread, qprofit, bprofit)")
        print("------------------------------------------------")
        for result in results:
            #print('Spread: {} q profit: {} b profit:{} \n'.format(result[0], result[1], result[2]))
            print("("+str(result[0])+","+str(result[1])+","+str(result[2])+","+str(result[3])+")")
        

    def handle_start_tuner(self):
        step = get_tuner_params_step()
        spread = get_tuner_params_spread()
        base = get_tuner_params_base()
        quote = get_tuner_params_quote()
        distribution_strategy = get_tuner_distribution_strategy()
        print("Params gotten")
        start_tuner(step, spread, base, quote, distribution_strategy)


    def start_statistikos(self):
        if no_price_data_table_exists():
            create_price_data_table()
        merkatos = get_all_merkatos()
        instances = []
        for merkato in merkatos:
            print(merkato['exchange'])
            if merkato['exchange'] == 'test':
                continue
            exchange = get_exchange(merkato['exchange'])
            exchange["public_api_key"]  = ''
            exchange["private_api_key"] = ''
            exchange_class = get_relevant_exchange(merkato['exchange'])
            exchange_instance = exchange_class(exchange, coin=merkato['alt'], base=merkato['base'])
            instances.append(exchange_instance)
        while True:
            for instance in instances:
                now = round(datetime.datetime.now().timestamp())
                last_trade_price = instance.get_last_trade_price()
                if last_trade_price == 'Error':
                    print('error on ' + instance.name)
                    continue
                insert_price_data(instance.name, last_trade_price, instance.ticker, now)
                # print('Price Data for {}_{}_{}'.format(instance.name, instance.coin, instance.base), context)
            time.sleep(60)

    

    def add_statistiko(self):
        if no_merkatos_table_exists():
            create_merkatos_table()
        if no_price_data_table_exists():
            create_price_data_table()
        exchange_name = self.get_exchange_name()
        quote_asset = self.get_quote_asset()
        base_asset = self.get_base_asset()
        exchange_pair = exchange_name + "coin={}_base={}".format(quote_asset, base_asset)
        insert_merkato(exchange=exchange_name, alt=quote_asset, base=base_asset, exchange_pair=exchange_pair)
        self.create_widgets()

    def get_exchange_name(self):
        print('Select Exchange')
        print('For Binance -> bina')
        print('For Kraken -> krak')
        print('For Tux -> tux')
        selection = input('Selection: ')
        if selection in ['bina', 'krak', 'tux']:
            return selection
        return self.get_exchange_name()

    def get_quote_asset(self):
        QUOTE_OPTIONS = ["XMR", "ETH", "PEPECASH"]
        print('Select Quote Asset')
        print('For XMR -> XMR')
        print('For PEPECASH -> PEPECASH')
        print('For ETH -> ETH')
        selection = input('Selection: ')
        if selection in QUOTE_OPTIONS:
            return selection
        return self.get_quote_asset()

    def get_base_asset(self):
        BASE_OPTIONS = ["BTC","USDT","ETH"]
        print('Select Base Asset')
        print('For BTC -> BTC')
        print('For USDT -> USDT')
        print('For ETH -> ETH')
        selection = input('Selection: ')
        if selection in BASE_OPTIONS:
            return selection
        return self.get_base_asset()

    def add_exchange(self):
        if no_exchanges_table_exists():
            create_exchanges_table()
        self.exchange = self.get_exchange_name()
        self.run_enter_api_key_info()

    def run_enter_api_key_info(self, message=""):
        if message != "":
            print(message)
        pub_key = ''
        priv_key = ''
        self.submit_api_keys(pub_key, priv_key)


    def submit_api_keys(self, public_key, private_key):
        self.public_api_key = public_key
        self.private_api_key = private_key
        config = {}
        config['public_api_key'] = public_key
        config['private_api_key'] = private_key
        config['limit_only'] = True
        config['exchange'] = self.exchange
        self.config = config

        if self.exchange == 'tux' or self.exchange == 'bina' or self.exchange == 'krak':
            valid_exchange = True
        else:
            print("Exchange not supported, this should never happen")
            valid_exchange = False

        if not valid_exchange:
            print("Wrong exchange try again")
            return

        else:
            print("Valid Exchange")
            # Call a new pane here, asking  for a password.
            self.submit_password(self.exchange)
            return


    def choose_exchange(self, exchange):
        self.exchange = exchange
        self.run_enter_api_key_info()


    def set_password(self):
        self.remove_all_widgets()
        password_message = tk.Label(self, anchor='n', padx = 10, text="Choose a password for encryption")
        password_field = tk.Entry(self, width=40)
        submit_password = tk.Button(self, command=lambda: self.submit_password(password_field.get()))
        submit_password["text"] = "Submit password"

        password_message.pack(side="top")
        password_field.pack(side="top")
        submit_password.pack(side="bottom")


    def submit_password(self, exchange):
        config = self.config
        insert_config_into_exchanges(config)
        self.create_widgets(exchange_added_text)


Application()
