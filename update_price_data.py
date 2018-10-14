from merkato.utils.database_utils import insert_price_data
from binance.client import Client


client = Client('', '')
klines = client.get_historical_klines("XMRBTC", Client.KLINE_INTERVAL_1MINUTE, "6 year ago UTC", "5 months ago UTC")
for line in klines:
	time = int(str(line[0])[:-3])
	open_price = line[1]
	high_price = line[2]
	low_price = line[3]

	open_to_high = float(high_price)-float(open_price)
	open_to_low = float(low_price)-float(open_price)

	high_closer_than_low = abs(open_to_high) < abs(open_to_low)
	#insert_price_data(exchange='bina', price=float(open_price), pair='XMRBTC', date=time)

	if high_closer_than_low:
		insert_price_data(exchange='bina', price=float(high_price), pair='XMRBTC', date=time)
		insert_price_data(exchange='bina', price=float(low_price), pair='XMRBTC', date=time+1)

	else:
		insert_price_data(exchange='bina', price=float(low_price), pair='XMRBTC', date=time)
		insert_price_data(exchange='bina', price=float(high_price), pair='XMRBTC', date=time+1)

