# NodeSet Validator Summary

A Python script to analyze Ethereum transactions for the NodeSet protocol, summarizing the number of validators managed by each operator based on successful transactions with the Multicall3 contract.

## Features
- Fetches transactions from Etherscan for the Multicall3 contract.
- Filters transactions referencing the NodeSet vault address.
- Summarizes the number of validators per operator.
- Logs detailed execution information to a file.

## Prerequisites
- Python 3.8 or higher
- An Etherscan API key (free tier available at [Etherscan](https://etherscan.io/apis))
- Access to an Ethereum node (e.g., local node or Infura)

## Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/nodeset-validator-summary.git
   cd nodeset-validator-summary
