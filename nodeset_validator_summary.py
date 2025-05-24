"""
NodeSet Validator Summary Script

This script analyzes Ethereum transactions for the NodeSet protocol using the Multicall3 contract.
It fetches transactions from Etherscan, filters for NodeSet-related transactions, and summarizes
the number of validators managed by each operator based on successful transactions.

Usage:
    Set environment variables:
        ETHERSCAN_API_KEY: Your Etherscan API key
        ETH_CLIENT_URL: Ethereum node URL (default: http://localhost:8545)
    Run: python nodeset_validator_summary.py
"""

import os
import logging
from collections import Counter
from time import sleep
import requests
from web3 import Web3
from requests.exceptions import HTTPError, RequestException

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    filename='nodeset_validator_summary.log',
    filemode='w',
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Constants
MULTICALL_ADDRESS = "0xcA11bde05977b3631167028862bE2a173976CA11"
NODESET_VAULT_ADDRESS = "0xB266274F55e784689e97b7E363B0666d92e6305B"
ETHERSCAN_API_URL = 'https://api.etherscan.io/api'
AGGREGATE_SIGNATURE = "0x252dba42"
PAGE_OFFSET = 1000
MAX_RETRIES = 3
RETRY_DELAY = 2

def setup_web3(eth_client_url: str) -> Web3:
    """Initialize and connect to an Ethereum node."""
    web3 = Web3(Web3.HTTPProvider(eth_client_url))
    if not web3.is_connected():
        logging.error("Failed to connect to Ethereum node at %s", eth_client_url)
        raise ConnectionError("Could not connect to Ethereum node")
    return web3

def fetch_multicall_transactions(api_key: str, multicall_address: str) -> list:
    """
    Fetch all transactions for the Multicall3 contract from Etherscan.

    Args:
        api_key: Etherscan API key.
        multicall_address: Multicall3 contract address (checksummed).
    
    Returns:
        List of transaction data.
    """
    all_transactions = []
    page = 1

    while True:
        params = {
            'module': 'account',
            'action': 'txlist',
            'address': multicall_address,
            'startblock': 0,
            'endblock': 99999999,
            'page': page,
            'offset': PAGE_OFFSET,
            'sort': 'desc',
            'apikey': api_key
        }
        for attempt in range(MAX_RETRIES):
            try:
                response = requests.get(ETHERSCAN_API_URL, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                if data.get('status') == '0':
                    logging.warning("No more transactions or API limit reached on page %d: %s", page, data.get('message'))
                    return all_transactions
                transactions = data.get('result', [])
                logging.info("Fetched %d transactions on page %d", len(transactions), page)
                all_transactions.extend(transactions)
                if len(transactions) < PAGE_OFFSET:
                    return all_transactions
                page += 1
                break
            except (HTTPError, RequestException) as e:
                if isinstance(e, HTTPError) and response.status_code == 429 and attempt < MAX_RETRIES - 1:
                    sleep(RETRY_DELAY * (2 ** attempt))
                    continue
                logging.error("Failed to fetch transactions on page %d: %s", page, str(e))
                return all_transactions
            except ValueError as e:
                logging.error("Invalid JSON response on page %d: %s", page, str(e))
                return all_transactions

    return all_transactions

def is_nodeset_transaction(tx: dict, vault_address: str) -> bool:
    """
    Check if a transaction is related to NodeSet by referencing the vault address.

    Args:
        tx: Transaction data from Etherscan.
        vault_address: NodeSet vault address (checksummed).
    
    Returns:
        True if the transaction is NodeSet-related, False otherwise.
    """
    input_data = tx.get('input', '').lower()
    if vault_address.lower()[2:] in input_data:
        return True
    return False

def summarize_validators_by_operator(api_key: str, eth_client_url: str) -> None:
    """
    Summarize the number of validators per operator based on successful Multicall3 transactions.

    Args:
        api_key: Etherscan API key.
        eth_client_url: Ethereum node URL.
    """
    web3 = setup_web3(eth_client_url)
    multicall_address = web3.to_checksum_address(MULTICALL_ADDRESS)
    vault_address = web3.to_checksum_address(NODESET_VAULT_ADDRESS)

    transactions = fetch_multicall_transactions(api_key, multicall_address)
    address_stats = {}

    for tx in transactions:
        input_data = tx.get('input', '')
        if input_data and len(input_data) >= 10 and input_data[:10].lower() == AGGREGATE_SIGNATURE.lower():
            from_address = web3.to_checksum_address(tx['from'])
            if not is_nodeset_transaction(tx, vault_address):
                continue
            logging.info("Found NodeSet Aggregate transaction from %s: %s", from_address, tx['hash'])
            if from_address not in address_stats:
                address_stats[from_address] = {'successful': 0}
            if int(tx.get('isError', '0')) == 0:
                address_stats[from_address]['successful'] += 1

    if not address_stats:
        logging.info("No NodeSet-related Aggregate transactions found.")
        print("No NodeSet-related Aggregate transactions found.")
        return

    validator_counts = Counter(stats['successful'] for stats in address_stats.values())
    sorted_counts = sorted(validator_counts.keys());
    total_validators = 0
    for validator_count in sorted_counts:
        operator_count = validator_counts[validator_count]
        print(f"Number of operators with {validator_count} validators: {operator_count}")
        total_validators += operator_count * validator_count

    """ assume equal ETH per validator """
    print(f"total validators: {total_validators}")
    print(f"max validators: {sorted_counts[-1]}")
    print(f"Net maximum asset exposure for highest operators: {sorted_counts[-1] / total_validators}")
    logging.info("Validator summary generated successfully.")

def main():
    """Main function to execute the validator summary."""
    api_key = os.getenv('ETHERSCAN_API_KEY')
    eth_client_url = os.getenv('ETH_CLIENT_URL', 'http://localhost:8545')
    
    if not api_key:
        logging.error("Etherscan API key not provided.")
        raise ValueError("Etherscan API key must be set in environment variable ETHERSCAN_API_KEY")
    
    summarize_validators_by_operator(api_key, eth_client_url)

if __name__ == "__main__":
    main()
