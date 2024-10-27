from sqlalchemy import create_engine
from sqlalchemy import text
import os


credentials = {
    "username": "i-can-only-read-gmx-data",
    "password": "house-football-checksum-11",
    "public ip": "34.77.163.253",
    "port": "5432",
    "db": "dojo_data"
}

connection_string = f'postgresql://{credentials["username"]}:{credentials["password"]}@{credentials["public ip"]}:{credentials["port"]}/{credentials["db"]}'

engine = create_engine(connection_string)
conn = engine.connect()

sql_query = conn.execute(text('''
    SELECT 
        contract, 
        ARRAY_AGG(block) AS blocks, 
        ARRAY_AGG(event_data) AS event_data, 
        ARRAY_AGG(block_timestamp) AS block_timestamps, 
        ARRAY_AGG(transaction_hash) AS transaction_hashes
    FROM hackathon_ethereum_events
    WHERE event_name = 'Swap'
    GROUP BY contract
'''))

fetched_data = sql_query.fetchall()

sql_query.close()

from web3 import Web3

w3 = Web3(Web3.HTTPProvider('https://rpc.ankr.com/eth/fb48370f4a2ef755e5926aff6a70d50399bfa8046830041bb4ffe84678ca1cb8'))

def get_pool_data(address):
    pool_abi = [
        {"constant": True, "inputs": [], "name": "token0", "outputs": [{"name": "", "type": "address"}], "type": "function"},
        {"constant": True, "inputs": [], "name": "token1", "outputs": [{"name": "", "type": "address"}], "type": "function"}
    ]
    
    token_abi = [
        {
            "constant": True,
            "inputs": [],
            "name": "name",
            "outputs": [{"name": "", "type": "string"}],
            "type": "function"
        },
        {
            "constant": True,
            "inputs": [],
            "name": "symbol",
            "outputs": [{"name": "", "type": "string"}],
            "type": "function"
        }
    ]
    
    pool_contract = w3.eth.contract(address=Web3.to_checksum_address(address), abi=pool_abi)
    
    token0_address = pool_contract.functions.token0().call()
    # For token0
    token0_contract = w3.eth.contract(address=Web3.to_checksum_address(token0_address), abi=token_abi)
    token0_name = token0_contract.functions.name().call()
    token0_symbol = token0_contract.functions.symbol().call()
    
    token1_address = pool_contract.functions.token1().call()
    # For token1
    token1_contract = w3.eth.contract(address=Web3.to_checksum_address(token1_address), abi=token_abi)
    token1_name = token1_contract.functions.name().call()
    token1_symbol = token1_contract.functions.symbol().call()
    
    # print(f"Pool: {address} - Token0: {token0_address} - {token0_name} - {token0_symbol}, Token1: {token1_address} - {token1_name} - {token1_symbol}")
    return {"token0": token0_symbol, "token1": token1_symbol}

import json

for i, contract in enumerate((x[0] for x in fetched_data)):
    address_data = {}
    contract_data = fetched_data[i][1:]
    
    pool_data = get_pool_data(contract)
    
    for j in range(len(contract_data[0])):
        tx_hash = contract_data[3][j]
        user_address = w3.eth.get_transaction_receipt(tx_hash)['from']
        
        tx_info = {
            "tx_hash": tx_hash,
            "user_address": user_address,
            "token0": pool_data["token0"],
            "amount0": contract_data[1][j]["amount0"],
            "token1": pool_data["token1"],
            "amount1": contract_data[1][j]["amount1"],
            "timestamp": contract_data[2][j],
            "pool_liquidity": contract_data[1][j]["liquidity"]
        }
        
        if (user_address in address_data):
            address_data[user_address].append(tx_info)
        else:
            address_data[user_address] = [tx_info]
    
    k = -1
    filename = f"data_{pool_data['token0']}_{pool_data['token1']}.json"
    if os.path.exists(filename):
        k = 0
    while os.path.exists(f"data_{pool_data['token0']}_{pool_data['token1']}_{k}.json"):
        k += 1
    if (k != -1):
        filename = f"data_{pool_data['token0']}_{pool_data['token1']}_{k}.json"
    
    with open(os.path.join("./pools",filename), "w") as file:
        json.dump(address_data, file, indent=4, default=str)
    
    print(f"Completed {i / (len(fetched_data) - 1) * 100}%/100%")
