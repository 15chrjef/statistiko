import sqlite3
import time
import json

pattern = '%Y-%m-%d %H:%M:%S'


conn = sqlite3.connect('merkato.db')

c = conn.cursor()
counter = 0
with open("price_data.txt") as infile:
    for line in infile:
        obj = json.loads(line)
        date = obj["price"][0]
        price = obj["price"][1]
        epoch = int(time.mktime(time.strptime(date, pattern)))
        print(epoch)
    
        c.execute("""REPLACE INTO price_data 
                    (exchange, pair, date, price) VALUES (?,?,?,?)""", ("bina", "XMRBTC", epoch, price))
        counter = counter + 1
        if counter % 500 == 0:
            conn.commit()
    conn.close()