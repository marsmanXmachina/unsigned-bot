

def get_min_prices(assets: list) -> list:
    min_price = min([asset.get("price") for asset in assets])
    return [asset for asset in assets if asset.get("price") == min_price]

def get_average_price(assets: list) -> float:
    num_assets = len(assets) 
    return sum_prices(assets)/num_assets if num_assets else 0  

def sum_prices(assets: list) -> float:
    return sum([asset.get("price") for asset in assets])