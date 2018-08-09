from merkato.merkato_config import load_config, get_config, create_config
from merkato.parser import parse
from merkato.utils.database_utils import no_merkatos_table_exists, create_merkatos_table, insert_merkato, get_all_merkatos, get_exchange, no_exchanges_table_exists, create_exchanges_table, drop_merkatos_table, drop_exchanges_table, insert_exchange, get_all_exchanges
from merkato.utils import generate_complete_merkato_configs, ensure_bytes, encrypt, decrypt, get_relevant_exchange
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
    print('exchange', exchange)
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
        print('Quit -> 4')
        selection = input('Selection: ')
        self.handle_welcome_selection(selection)


    def handle_welcome_selection(self, selection):
        if selection == '1':
            self.start_statistikos()
        elif selection == '2':
            self.add_statistiko()
        elif selection == '3':
            self.add_exchange()
        else:
            return

    def start_statistikos(self):
        merkatos = get_all_merkatos()
        instances = []
        for merkato in merkatos:
            print('merkato', merkato)
            exchange = get_exchange(merkato['exchange'])
            print('exchange', exchange)
            password = getpass.getpass('Enter password for {}'.format(merkato['exchange']))
            decrypt_keys(exchange, password)
            exchange_class = get_relevant_exchange(merkato['exchange'])
            exchange_instance = exchange_class(exchange, coin=merkato['alt'], base=merkato['base'])
            instances.append(exchange_instance)
        while True:
            for instance in instances:
                now = str(datetime.datetime.now().isoformat()[:-7].replace("T", " "))
                last_trade_price = instance.get_last_trade_price()
                context = {"price": (now, last_trade_price)}
                print('Price Data for {}_{}_{}'.format(instance.name, instance.coin, instance.base), context)
                f = open("price_data.txt", "a")
                f.write(json.dumps(context))
            time.sleep(60)

    def add_statistiko(self):
        if no_merkatos_table_exists():
            create_merkatos_table()
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
        pub_key = getpass.getpass('Enter Public Key:')
        priv_key = getpass.getpass('Enter Private Key:')
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

        if self.exchange == 'tux':
            credentials_are_valid = validate_credentials(config)

        elif self.exchange == 'bina':
            credentials_are_valid = validate_keys(config)

        elif self.exchange == 'krak':
            credentials_are_valid = validate_kraken(config)

        else:
            "Exchange not supported, this should never happen"
            credentials_are_valid = False

        if not credentials_are_valid:
            print("API Keys Invalid")
            self.run_enter_api_key_info("API keys invalid, please try again.")
            return

        else:
            print("API keys valid")
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
        print('Enter password for {}'.format(exchange))
        password = getpass.getpass('Selection: ') 
        config = self.config
        encrypt_keys(config, password)
        insert_config_into_exchanges(config)
        decrypt_keys(config, password)
        self.create_widgets(exchange_added_text)


Application()
