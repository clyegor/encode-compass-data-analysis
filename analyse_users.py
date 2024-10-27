import json
import pandas as pd
from glob import glob

# Define decimals map for tokens
DECIMALS_MAP = {
    "WETH": 10 ** 18,
    "DAI": 10 ** 18,
    "USDC": 10 ** 6,
    "USDT": 10 ** 6,
    "WBTC": 10 ** 8,
    "LINK": 10 ** 18,
    "UNI": 10 ** 18,
    "MKR": 10 ** 18,
    "MATIC": 10 ** 18,
    "SHIB": 10 ** 18,
    "LDO": 10 ** 18,
    "PEPE": 10 ** 18,
    "SKL": 10 ** 18
}

# Define the specific pools you want to load
TARGET_POOLS = ["WETH_USDT", "USDC_WETH", "MATIC_WETH", "UNI_WETH", "DAI_WETH"]

def load_pool_data():
    # Load and filter data from only the specified pool files
    pool_files = glob("pools/data_*.json")  # Adjust path if needed
    pool_files = [file for file in pool_files if any(pool in file for pool in TARGET_POOLS)]
    
    all_records = []

    for file in pool_files:
        token0, token1 = file.split("_")[1:]
        token1 = token1.split(".")[0]
        
        with open(file) as f:
            data = json.load(f)
        
        # Convert JSON data into a DataFrame
        records = []
        for user_address, transactions in data.items():
            for tx in transactions:
                records.append(tx)
        
        df = pd.DataFrame(records)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df[f'amount0_{token0}'] = df['amount0'] / DECIMALS_MAP[token0]
        df[f'amount1_{token1}'] = df['amount1'] / DECIMALS_MAP[token1]
        df = df[(df[f'amount0_{token0}'] != 0) & (df[f'amount1_{token1}'] != 0)]
        all_records.append(df)

    # Combine all pools data into a single DataFrame
    all_df = pd.concat(all_records, ignore_index=True)
    return all_df

def load_usdt_prices():
    # Load historical USDT prices for each token
    usdt_prices = pd.read_csv('Combined_Historical_Price_Data.csv')  # Assumes 'Date', 'Token', 'Price_USDT'
    usdt_prices['Date'] = pd.to_datetime(usdt_prices['Date'], dayfirst=True)
    usdt_prices = usdt_prices.set_index(['Date', 'token'])
    usdt_prices['Price'] = usdt_prices['Price'].str.replace(',', '').astype(float)
    
    return usdt_prices

def get_usdt_price(token, date, usdt_prices):
    """Retrieve USDT price for a specific token on a given date."""
    if token in {"USDT", "USDC", "DAI", "FRAX", "LDO"}:
        return 1  # Price is 1 if token is a stablecoin
    token_adj = "ETH" if token == "WETH" else "BTC" if token == "WBTC" else token
    try:
        return usdt_prices.loc[(pd.to_datetime(date), token_adj), 'Price']
    except KeyError:
        return None  # Return None if price is missing


def calculate_user_perfomance(user_data, usdt_prices):
    my_total_balance_usdt = 0  # Final balance in USDT
    intermediate_balances = {}  # Track intermediate balances for each token
    token_volumes = {}
    txs = {"buy": 0, "sell": 0}
    tokens_bought = {}
    
    for _, row in user_data.iterrows():
        date = row['timestamp'].date().strftime('%Y-%m-%d')
        token0, token1 = row['token0'], row['token1']
        
        t0_usd = token0 in {"USDT", "USDC", "DAI", "FRAX", "LDO"}
        t1_usd = token1 in {"USDT", "USDC", "DAI", "FRAX", "LDO"}
        amount0 = row[f'amount0_{token0}']
        amount1 = row[f'amount1_{token1}']
        
        # Retrieve USDT prices for token0 and token1 on this date
        if t0_usd:
            price_token0_usdt = 1
        else:
            price_token0_usdt = get_usdt_price(token0, date, usdt_prices)
        
        if t1_usd:
            price_token1_usdt = 1
        else:
            price_token1_usdt = get_usdt_price(token1, date, usdt_prices)
        
        if price_token0_usdt is None or price_token1_usdt is None:
            continue  # Skip this transaction if either price is missing
        
        # Initialize intermediate balance if it doesn’t exist
        if token0 not in intermediate_balances:
            intermediate_balances[token0] = 0
            tokens_bought[token0] = None
        if token1 not in intermediate_balances:
            intermediate_balances[token1] = 0
            tokens_bought[token1] = None
        
        # Update volumes for each transaction
        if token0 not in token_volumes:
            token_volumes[token0] = 0
        if token1 not in token_volumes:
            token_volumes[token1] = 0
        
        token_volumes[token0] += abs(amount0)
        token_volumes[token1] += abs(amount1)
        
        # Update intermediate balances and calculate realized values
        if amount0 < 0:  # Bought token0 using token1
            my_total_balance_usdt = handle_buy_tx(txs, tokens_bought, token0, token1, date, 
                  t0_usd, t1_usd, amount0, amount1, 
                  intermediate_balances,
                  price_token1_usdt, my_total_balance_usdt)
        else:  # Sold token0 to get token1
            my_total_balance_usdt = handle_sell_tx(txs, tokens_bought, token0, token1, date, 
                  t0_usd, t1_usd, amount0, amount1, 
                  intermediate_balances,
                  price_token0_usdt, my_total_balance_usdt)
    
    my_total_balance_usdt = finalize_balances(intermediate_balances, usdt_prices, tokens_bought, my_total_balance_usdt)
    
    # Choose only active users
    if (txs["buy"] > 25 and txs["sell"] > 25):
        # Store the user's performance in terms of USDT
        return my_total_balance_usdt, token_volumes
    return None, None

def handle_buy_tx(txs, tokens_bought, token0, token1, date, 
                  t0_usd, t1_usd, amount0, amount1, 
                  intermediate_balances,
                  price_token1_usdt, my_total_balance_usdt):
    txs['buy'] += 1
    tokens_bought[token0] = date
    # Buying token0, spending token1
    if t0_usd:
        my_total_balance_usdt += abs(amount0)
    else:
        intermediate_balances[token0] += abs(amount0)  # Increase intermediate balance of token0
    
    if t1_usd:
        my_total_balance_usdt -= amount1 * price_token1_usdt  # Deduct the cost in USDT terms
    else:
        sell_amount = min(amount1, intermediate_balances[token1])  # Only sell up to available balance
        gain_in_usdt = sell_amount * price_token1_usdt  # Calculate gain in USDT terms
        my_total_balance_usdt += gain_in_usdt  # Add gain to total USDT balance
        
        # Adjust intermediate balance for token0
        intermediate_balances[token1] -= sell_amount
        
        my_total_balance_usdt -= (amount1 - sell_amount) * price_token1_usdt
    return my_total_balance_usdt

def handle_sell_tx(txs, tokens_bought, token0, token1, date, 
                  t0_usd, t1_usd, amount0, amount1, 
                  intermediate_balances,
                  price_token0_usdt, my_total_balance_usdt):
    txs['sell'] += 1
    tokens_bought[token1] = date
    if t1_usd:
        my_total_balance_usdt += abs(amount1)
    else:
        intermediate_balances[token1] += abs(amount1)  # Increase intermediate balance of token1
    
    # Selling token0, receiving token1
    if t0_usd:
        my_total_balance_usdt -= amount0
    else:
        sell_amount = min(amount0, intermediate_balances[token0])  # Only sell up to available balance
        gain_in_usdt = sell_amount * price_token0_usdt  # Calculate gain in USDT terms
        my_total_balance_usdt += gain_in_usdt  # Add gain to total USDT balance
        
        # Adjust intermediate balance for token0
        intermediate_balances[token0] -= sell_amount
        
        my_total_balance_usdt -= (amount0 - sell_amount) * price_token0_usdt
    return my_total_balance_usdt

def finalize_balances(intermediate_balances, usdt_prices, tokens_bought, my_total_balance_usdt):
    # Finalize remaining intermediate balances at the last known prices
    for token, balance in intermediate_balances.items():
        if balance > 0:
            token_updated = "ETH" if token == "WETH" else "BTC" if token == "WBTC" else "USD" if \
                token in {"USDT", "USDC", "DAI", "FRAX", "LDO"} else token
            
            last_price_usdt = usdt_prices.loc[(tokens_bought[token], token_updated), 'Price']
            my_total_balance_usdt += balance * last_price_usdt  # Add remaining balance value
    return my_total_balance_usdt

def main():
    all_df = load_pool_data()
    usdt_prices = load_usdt_prices()
    
    # Group by user and analyze performance across pools
    user_performance = []
    user_performance_expanded = []
    for user, user_data in all_df.groupby('user_address'):
        user_total_balance_usdt, token_volumes = calculate_user_perfomance(user_data, usdt_prices)
        
        if user_total_balance_usdt:
            user_performance.append({'user_address': user, 'profit_in_usdt': user_total_balance_usdt})
            user_performance_expanded.append({
                'user_address': user, 
                'profit_in_usdt': user_total_balance_usdt,
                'volume_traded': token_volumes
                })
    
    # Convert to DataFrame for sorting and selecting top performers
    performance_df = pd.DataFrame(user_performance)
    performance_df_sorted = performance_df.sort_values(by='profit_in_usdt', ascending=False)
    top_performers = performance_df_sorted.head(100)
    print(top_performers)

    top_performers['user_address'].to_csv("top_performers_weth_usdt.txt", index=False, header=False)
    
    
    performance_df = pd.DataFrame(user_performance_expanded)
    performance_df_sorted = performance_df.sort_values(by='profit_in_usdt', ascending=False)
    top_performers = performance_df_sorted.head(100)
    top_performers.to_csv("top_performers_with_profits_and_volumes.csv", index=False)


if __name__ == "__main__":
    main()