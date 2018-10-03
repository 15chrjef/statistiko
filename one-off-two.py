import sqlite3
import time
import json

pattern = '%Y-%m-%d %H:%M:%S'


conn = sqlite3.connect('merkato.db')

c = conn.cursor()
counter = 0
with open("latest_three_months.test") as infile:
    for line in infile:
        array = eval(line) # Never do this with untrusted data
        timestamp = str(array[0])[:-3] # Truncate milliseconds
        open_price = array[1]
        print(timestamp)
    
        c.execute("""REPLACE INTO price_data 
                    (exchange, pair, date, price) VALUES (?,?,?,?)""", ("bina", "XMRBTC", timestamp, open_price))
        counter = counter + 1
        if counter % 500 == 0:
            conn.commit()
    conn.close()