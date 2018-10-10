from merkato.utils.database_utils import insert_price_data
from binance.client import Client


client = Client('', '')
klines = client.get_historical_klines("XMRBTC", Client.KLINE_INTERVAL_1MINUTE, "3 weeks ago UTC")
for line in klines:
	time = int(str(line[0])[:-3])
	open_price = line[1]
	insert_price_data(exchange='bina', price=float(open_price), pair='XMRBTC', date=time)

