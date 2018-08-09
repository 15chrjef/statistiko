import krakenex

import logging
log = logging.getLogger(__name__)

def validate_kraken(config):
    public_key = config["public_api_key"]
    private_key = config["private_api_key"]
    client = krakenex.API(public_key, private_key)

    try:
        client.query_public('Ticker', {'pair': 'XMRXBT'})
    except Exception as e:
        log.error(e)
        return False

    return True