import requests


NOBITEX_API_URL = "https://apiv2.nobitex.ir/v3/orderbook/USDTIRT"


def get_usdt_price():
    response = requests.get(
        NOBITEX_API_URL,
        timeout=10
    )

    response.raise_for_status()

    data = response.json()

    asks = data.get("asks", [])
    bids = data.get("bids", [])

    if not asks or not bids:
        raise ValueError("قیمت USDT در پاسخ نوبیتکس پیدا نشد.")

    ask_price = float(asks[0][0])
    bid_price = float(bids[0][0])

    return {
        "buy": ask_price,
        "sell": bid_price,
    }
