import pandas as pd
import matplotlib.pyplot as plt
import json
import plotly.graph_objects as go

# Load the data from CSV or define a sample dataset here
data = pd.read_csv("top_performers_with_profits_and_volumes.csv")

# Convert the JSON string of volumes to a dictionary
data['volume_traded'] = data['volume_traded'].apply(lambda x: json.loads(x.replace("'", '"')))

# Load the USDT price data for each token for standardization
usdt_prices = {
    'WETH': 2525.04,  # example price in USDT
    'MATIC': 0.33,  # example price in USDT
    'UNI': 7.54    # example price in USDT
}

usdt_equivalent_volumes = []
user_addresses = []

# Convert all non-USDT/USDC volumes to their equivalent USDT values
for index, row in data.iterrows():
    volumes = {}
    for token, volume in row['volume_traded'].items():
        if token in {"USDT", "USDC"}:
            volumes[token] = volume
        elif token in usdt_prices:
            volumes[token] = volume * usdt_prices[token]
    usdt_equivalent_volumes.append(volumes)
    user_addresses.append(row['user_address'])  

# Convert usdt_equivalent_volumes list to a DataFrame
volume_df = pd.DataFrame(usdt_equivalent_volumes)
volume_df['user_address'] = user_addresses

volume_df.set_index('user_address', inplace=True)

# Create the stacked bar chart with Plotly
fig = go.Figure()

# Add a trace for each cryptocurrency
for token in volume_df.columns:
    fig.add_trace(go.Bar(
        x=volume_df.index,
        y=volume_df[token],
        name=token
    ))

# Customize layout
fig.update_layout(
    title="User Traded Volume in USDT Equivalent",
    xaxis_title="User Address",
    yaxis_title="Volume in USDT",
    barmode='stack',
    legend_title="Token",
)

# Show the plot
fig.show()