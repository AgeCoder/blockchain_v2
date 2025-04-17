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
TARGET_BLOCK_TIME = 600 

# Transaction Configuration
DEFAULT_FEE_RATE = 0.0001  # Default fee per byte
MIN_FEE = 0.0001          # Minimum transaction fee
BASE_TX_SIZE = 250        # Base transaction size in bytes

# Mining Configuration
BLOCK_SUBSIDY = 50        # Starting block reward
