import json
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

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
}

# Load USDC_WETH and USDT_WETH data, and combine
TOKEN_PAIRS = [("USDC", "WETH"), ("WETH", "USDT"), ("MATIC", "WETH"), ("UNI", "WETH"), ("DAI", "WETH")]

def load_pool_data():
    all_dataframes = []
    for token0, token1 in TOKEN_PAIRS:
        with open(f"pools/data_{token0}_{token1}.json") as file:
            data = json.load(file)
        
        # Convert JSON data into a DataFrame
        records = []
        for _, transactions in data.items():
            for tx in transactions:
                records.append(tx)
        dataframe = pd.DataFrame(records)
        all_dataframes.append(dataframe)
    return all_dataframes

def load_usdt_prices():
    usdt_prices = pd.read_csv('Combined_Historical_Price_Data.csv')
    usdt_prices['Date'] = pd.to_datetime(usdt_prices['Date'])
    usdt_prices = usdt_prices.set_index(['Date', 'token'])
    usdt_prices['Price'] = usdt_prices['Price'].str.replace(',', '').astype(float)
    return usdt_prices

def get_price(row, usdt_prices):
    date_str = datetime.strftime(pd.to_datetime(row['timestamp']), "%d/%m/%Y")
    try:
        return usdt_prices.loc[(date_str, row['token0']), 'Price']
    except KeyError:
        return None  # or use np.nan to indicate missing data

def transform_df(df, token, usdt_prices):
    df['rate'] = df.apply(lambda row: get_price(row, usdt_prices), axis=1)
    df.dropna(subset=['rate'], inplace=True)  # Drop rows where rate is missing
    df['amount0'] = (df['amount0'] / DECIMALS_MAP[token] * df['rate'] * 10 ** 6)
    df['token0'] = 'USDT'
    return df

def load_eth_data():
    # Load the ETH price data and calculate volatility
    eth_price_data = pd.read_csv('Ethereum Historical Results Price Data.csv')
    eth_price_data['Date'] = pd.to_datetime(eth_price_data['Date'], format='%d/%m/%Y').dt.date
    eth_price_data['Price'] = eth_price_data['Price'].str.replace(',', '').astype(float)
    eth_price_data = eth_price_data[['Date', 'Price']].iloc[::-1]
    eth_price_data['Volatility'] = eth_price_data['Price'].pct_change().abs() * 100
    return eth_price_data

def clean_the_df(df, positive_addresses):
    # Assuming 'df' is the DataFrame with transaction data, filter it
    df = df[df['user_address'].isin(positive_addresses)]

    # Convert timestamps and amounts to numeric
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['amount0'] = df.apply(lambda row: row['amount0'] / DECIMALS_MAP[row['token0']], axis=1)

    # Calculate volume
    df['volume'] = abs(df['amount0'])
    df['date'] = df['timestamp'].dt.date
    
    return df

def plot(daily_total_volume, filtered_volatility_data, hover_text, correlation):
    # Plotting daily total volume and ETH volatility on the same chart
    fig = go.Figure()

    # Add total volume to the chart
    fig.add_trace(go.Scatter(
        x=daily_total_volume.index,
        y=daily_total_volume.values,
        mode="lines+markers",
        name="Daily Total Volume",
        text=hover_text,
        hoverinfo="text"
    ))

    # Add ETH volatility to the chart
    fig.add_trace(go.Scatter(
        x=filtered_volatility_data['Date'],
        y=filtered_volatility_data['Volatility'],
        mode="lines",
        name="ETH Daily Volatility (%)",
        yaxis="y2"
    ))

    # Update layout to accommodate dual y-axes and ensure sorted dates are displayed
    fig.update_layout(
        title=f"Daily Total Volume for Combined Pools and ETH Volatility. Correlation: {correlation:.2f}",
        xaxis_title="Date",
        yaxis=dict(title="Total Volume", side="left"),
        yaxis2=dict(
            title="ETH Volatility (%)", 
            overlaying='y',
            side='right'
        ),
        legend_title="Metric",
        xaxis=dict(type="date")
    )

    fig.show()
    

def main():
    usdt_prices = load_usdt_prices()
    all_dataframes = load_pool_data()
    
    all_dataframes[2] = transform_df(all_dataframes[2], "MATIC", usdt_prices)
    all_dataframes[3] = transform_df(all_dataframes[3], "UNI", usdt_prices)
   
    all_dataframes[1].rename(columns={"token0": "token1", "token1": "token0", "amount0": "amount1", "amount1": "amount0"}, inplace=True)

    df = pd.concat(all_dataframes, ignore_index=True)

    with open("top_performers_weth_usdt.txt", "r") as file:
        positive_addresses = file.read().splitlines()

    df = clean_the_df(df, positive_addresses)
    
    # Calculate total transaction volume per day
    daily_total_volume = df.groupby('date')['volume'].sum()

    # Sort the daily total volume by date
    daily_total_volume = daily_total_volume.sort_index()

    eth_price_data = load_eth_data()
    
    # Filter ETH volatility data for dates where transactions occurred and sort by date
    filtered_volatility_data = eth_price_data[eth_price_data['Date'].isin(daily_total_volume.index)]
    filtered_volatility_data = filtered_volatility_data.sort_values(by='Date')

    # Prepare hover text for the total volume trace
    hover_text = [
        f"Date: {date}<br>Total Volume: {volume:.2f}<br>Tx Count: {daily_total_volume[date]}"
        for date, volume in zip(daily_total_volume.index, daily_total_volume.values)
    ]

    # Correlation Analysis
    # Merge the total volume and volatility data on dates where both exist
    merged_data = pd.DataFrame({
        'date': daily_total_volume.index,
        'total_volume': daily_total_volume.values,
    }).merge(
        filtered_volatility_data[['Date', 'Volatility']].rename(columns={'Date': 'date'}),
        on='date'
    )

    # Calculate correlation between total volume and ETH volatility
    correlation = merged_data['total_volume'].corr(merged_data['Volatility'])
    
    plot(daily_total_volume, filtered_volatility_data, hover_text, correlation)

if __name__ == "__main__":
    main()
