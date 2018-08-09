from merkato.merkato_config import load_config, get_config, create_config
from merkato.parser import parse
from merkato.utils.database_utils import no_merkatos_table_exists, create_merkatos_table, insert_merkato, get_all_merkatos, get_exchange, no_exchanges_table_exists, create_exchanges_table, drop_merkatos_table, drop_exchanges_table, insert_exchange, get_exchange
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
    def __init__(self, master=None):
        super().__init__(master)
        self.base = "BTC"
        self.coin = "XMR"
        self.spread = .02
        self.coin_reserve = 17
        self.base_reserve = .4
        self.pack()
        self.create_widgets()


    def create_widgets(self, message=None):
        self.remove_all_widgets()
        if message == None:
            message = welcome_txt

        welcome_message = tk.Label(self, anchor='n', padx = 10, text=message)
        welcome_message.pack(side="top")
      
        run_merkatos = tk.Button(self, command=self.get_assets)
        run_merkatos["text"] = "Run statistikos"
        run_merkatos.pack(side="top")

        create_new = tk.Button(self, command=self.start_create_frame)
        create_new["text"] = "Add Exchange"
        create_new.pack(side="top")

        quit = tk.Button(self, text="QUIT", fg="red", command=root.destroy)
        quit.pack(side="top")


    def start_statistiko(self, password, base, quote, exchange):
        root.destroy()
        exchange_config = get_exchange(exchange)
        decrypt_keys(exchange_config, password)
        exchange_class = get_relevant_exchange(exchange)
        self.exchange = exchange_class(exchange_config, coin=quote, base=base)
        while True:
            now = str(datetime.datetime.now().isoformat()[:-7].replace("T", " "))
            last_trade_price = self.exchange.get_last_trade_price()
            context = {"price": (now, last_trade_price)}
            print('context', context)
            f = open("price_data.txt", "a")
            f.write(json.dumps(context))
            time.sleep(60)

    def start_create_frame(self):
        self.run_remove_tables_prompts()


    def remove_all_widgets(self):
        for widget in self.winfo_children():
            widget.destroy()


    def run_remove_tables_prompts(self):
        if no_merkatos_table_exists():
            create_merkatos_table()
            self.run_remove_exchanges_prompts()
        else:
            self.run_remove_merkatos_prompt()


    def run_remove_merkatos_prompt(self):
        self.remove_all_widgets()
        drop_merkatos_message = tk.Label(self, anchor='n', padx = 10, text=drop_merkatos_txt).pack(side="top")
        
        drop_merkatos = tk.Button(self, command=self.drop_merkatos_table)
        drop_merkatos["text"] = "Yes"
        drop_merkatos.pack(side="bottom")
      
        dont_drop_merkatos = tk.Button(self, command=self.dont_drop_merkatos_table)
        dont_drop_merkatos["text"] = "No"
        dont_drop_merkatos.pack(side="bottom")


    def run_remove_exchanges_prompts(self):
        self.remove_all_widgets()
        drop_merkatos_message = tk.Label(self, anchor='n', padx = 10, text=drop_exchanges_txt).pack(side="top")

        drop_exchanges = tk.Button(self, command=self.drop_exchanges_table)
        drop_exchanges["text"] = "Yes"
        drop_exchanges.pack(side="bottom")
      
        dont_drop_exchanges = tk.Button(self, command=self.dont_drop_exchanges_table)
        dont_drop_exchanges["text"] = "No"
        dont_drop_exchanges.pack(side="bottom")


    def run_enter_api_key_info(self, message=""):
        self.remove_all_widgets()
        if message != "":
            warning = tk.Label(self, anchor='n', padx = 10, text=message, fg="red").pack(side="top")

        public_key_field = tk.Entry(self, width=40)
        private_key_field = tk.Entry(self, width=40)

        private_key_message = tk.Label(self, anchor='n', padx = 10, text=private_key_text)
        public_key_message = tk.Label(self, anchor='n', padx = 10, text=public_key_text)

        submit_keys = tk.Button(self, command= lambda: self.submit_api_keys(public_key_field.get(), private_key_field.get()))
        submit_keys["text"] = "Submit keys"

        public_key_field.pack(side="top")
        public_key_message.pack(side="top")

        private_key_field.pack(side="top")
        private_key_message.pack(side="top")

        submit_keys.pack(side="bottom")


    def drop_merkatos_table(self):
        drop_merkatos_table()
        self.run_remove_exchanges_prompts()


    def dont_drop_merkatos_table(self):
        self.run_remove_exchanges_prompts()


    def drop_exchanges_table(self):
        drop_exchanges_table()
        self.run_select_exchange_prompt()


    def dont_drop_exchanges_table(self):
        self.run_select_exchange_prompt()


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
            self.set_password()
            return


    def run_select_exchange_prompt(self):
        self.remove_all_widgets()
        select_exchange_message = tk.Label(self, anchor='n', padx = 10, text=exchange_select_txt).pack(side="top")
        
        select_exchange_binance = tk.Button(self, command= lambda: self.choose_exchange('bina'))
        select_exchange_binance["text"] = "Binance"
        select_exchange_binance.pack(side="bottom")

        select_exchange_tux = tk.Button(self, command= lambda: self.choose_exchange('tux'))
        select_exchange_tux["text"] = "Tux"
        select_exchange_tux.pack(side="bottom")

        select_exchange_tux = tk.Button(self, command= lambda: self.choose_exchange('krak'))
        select_exchange_tux["text"] = "Kraken"
        select_exchange_tux.pack(side="bottom")


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


    def submit_password(self, password):
        self.remove_all_widgets()
        config = self.config
        encrypt_keys(config, password)
        insert_config_into_exchanges(config)
        decrypt_keys(config, password)
        self.create_widgets(exchange_added_text)

    def enter_password(self, base, quote, exchange):
        self.remove_all_widgets()
        password_message = tk.Label(self, anchor='n', padx = 10, text="Enter password for decryption")
        password_field = tk.Entry(self, width=40)
        submit_password = tk.Button(self, command=lambda: self.start_statistiko(password_field.get(), base, quote, exchange))
        submit_password["text"] = "Submit password"

        password_message.pack(side="top")
        password_field.pack(side="top")
        submit_password.pack(side="bottom")
        
        

    def get_assets(self):
        self.remove_all_widgets()
        password_message = tk.Label(self, anchor='n', padx = 10, text="Select Desired Assets")
        base_label = tk.Label(self, anchor='n', padx = 10, text="Base Asset")
        quote_label = tk.Label(self, anchor='n', padx = 10, text="Quote Asset")
        exchange_label = tk.Label(self, anchor='n', padx = 10, text="Exchange")

        BASE_OPTIONS = ["BTC","USDT","ETH"]
        QUOTE_OPTIONS = ["XMR", "ETH", "PEPECASH"]
        EXCHANGE_OPTIONS = ["bina", 'tux', 'krak']

        base_variable = tk.StringVar(self)
        quote_variable = tk.StringVar(self)
        exchange_variable = tk.StringVar(self)

        base_variable.set(BASE_OPTIONS[0]) # default value
        quote_variable.set(QUOTE_OPTIONS[0])
        exchange_variable.set(EXCHANGE_OPTIONS[0])

        base_menu = tk.OptionMenu(self, base_variable, *BASE_OPTIONS)
        quote_menu = tk.OptionMenu(self, quote_variable, *QUOTE_OPTIONS)
        exchange_menu = tk.OptionMenu(self, exchange_variable, *EXCHANGE_OPTIONS)

        submit_password = tk.Button(self, command=lambda: self.enter_password(base_variable.get(), quote_variable.get(), exchange_variable.get()))
        submit_password["text"] = "Submit"

        submit_password.pack(side="bottom")
        quote_menu.pack(side="bottom")
        quote_label.pack(side="bottom")
        base_menu.pack(side="bottom")
        base_label.pack(side="bottom")
        base_menu.pack(side="bottom")
        base_label.pack(side="bottom")
        exchange_menu.pack(side="bottom")
        exchange_label.pack(side="bottom")

        password_message.pack(side="top")


root = tk.Tk()
app = Application(master=root)
app.mainloop()