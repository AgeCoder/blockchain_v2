import os
import time
NANOSECONDS = 1
MICROSECONDS  = 1000 * NANOSECONDS
MILLISECONDS  = 1000 * MICROSECONDS
SECONDS  = 1000 * MILLISECONDS  

MINRATE = 4 * SECONDS

STARTING_BALANCE = 1000

MINING_REWARD = 50
MINING_REWARD_INPUT = { 'address' : "*--offical-minning-reward--*"}

BLOCK_SIZE_LIMIT=1000000

HALVING_INTERVAL = 210000  # Blocks between halvings

# Transaction Configuration
MIN_FEE = 0.001          # Minimum transaction fee
BASE_TX_SIZE = 250        # Base transaction size in bytes

# Blockchain constants (keep existing)
BLOCK_SUBSIDY = 50 # Example value
TARGET_BLOCK_TIME = 60 # Example value (seconds)
MINRATE = 1 # Minimum time between blocks for difficulty adjustment (seconds)

# Transaction constants
DEFAULT_FEE_RATE = 0.00001 # Fee per byte (example)

# BOOT_NODE = 'wss://boot-node.onrender.com'
BOOT_NODE = 'ws://localhost:9000'


