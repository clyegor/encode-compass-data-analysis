# Ethereum and Arbitrum Events Data Analysis
This Jupyter Notebook aims to analyze events data from the Ethereum and Arbitrum blockchains. By leveraging Python's data analysis and visualization libraries, we will extract, process, and visualize data to identify significant patterns, trends, and insights within these blockchains' transaction events.

# Project Overview
Blockchain technologies like Ethereum and Arbitrum produce massive amounts of event data, reflecting user interactions, contract executions, and token movements. This project focuses on exploring this data to uncover valuable information, such as transaction trends, event frequencies, and any outliers or notable anomalies. Our analysis should offer insights into how these networks are being used, variations in activity between them, and possible factors influencing these variations.

# Postgresql Database Details
Host: 34.77.163.253
Port: 5432
Database: dojo_data
Username: i-can-only-read-gmx-data
Password: house-football-checksum-11

# Data Extraction
Using SQL queries, we fetch the top 100,000 events ordered by block_timestamp from the Ethereum and Arbitrum tables within our PostgreSQL database. While setting the seed for reproducibility.

# Exploratory Data Analysis

Using .value_counts(), we identify the distinct event types and their counts for the Arbitrum dataset. This provides an overview of which events are most common.

The find_event_ratio function calculates the frequency ratios of event types. Events that constitute less than 2% of the total are grouped under the category "others" to reduce chart complexity.

A dual pie chart visualization, using Plotly, shows the distribution of event types between Ethereum and Arbitrum. The charts provide a clear, visual comparison of event types across the two blockchains. The output gives us a clear view of which events are most common on each network. We can see that Swaps are the most prominent event so we shall focus on that.

To gain a clearer picture of event structures, we extract and format each distinct event type with its associated data fields. This process identifies each event type and displays its data fields, helping us understand the event-specific data structures for Ethereum and Arbitrum.

We will then normalize the data for each feature with min max scaler.

We can then plot a 3d scatter plot with a colorbar for 4 features which are; gas_cost, liqudity, sqrt price and trade volume (both amounts added). And from the plot we can't seem to find any correlation, but we do see that gas costs are low when liquidity is high for some cases. We will now look more into gas costs to see if there is a seasonal pattern.

We then make a function plot the moving average of gas cost prices and gas volume with a rolling window of 30 timestamps.

Here we see that in both currencies there is a slight seasonal pattern and there is a higher volatility for gas volume in compared to gas price, and that ethereum has a higher volatility on average.

# A more in depth analysis on swaps and contracts
