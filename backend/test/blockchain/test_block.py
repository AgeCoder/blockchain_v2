import time
import pytest

from backend.blockchain.block import Block , GENESIS_DATA
from backend.config import MINRATE, SECONDS
from backend.utils.hex_to_binary import hex_to_binary


def test_mine_block():
    last_block = Block.genesis()
    data = "test_block"
    block = Block.min_block(last_block,data)

    assert isinstance(block,Block)
    assert block.data == data
    assert block.last_hash == last_block.hash
    assert hex_to_binary(block.hash)[0:block.difficulty] == '0'*block.difficulty

def test_genesis():
    genesis = Block.genesis()
    
    assert isinstance(genesis,Block)
    assert genesis.timestamp == GENESIS_DATA['timestamp']
    assert genesis.data == GENESIS_DATA['data']
    assert genesis.hash == GENESIS_DATA['hash']
    assert genesis.last_hash == GENESIS_DATA['last_hash']

def test_quick_mined_block():
    last_block = Block.min_block(Block.genesis(),'vmr')
    mined_block = Block.min_block(last_block,'age')

    assert mined_block.difficulty == last_block.difficulty + 1

def test_slowly_mined_block():
    last_block = Block.min_block(Block.genesis(),'vmr')
    time.sleep(MINRATE/SECONDS)
    mined_block = Block.min_block(last_block,'age')

    assert mined_block.difficulty == last_block.difficulty - 1

def test_mined_block_difficulty_limits_at_1():
    last_block = Block(
        time.time_ns(),
        'test_last_block',
        'test_hash',
        'test_data',
        1,
        0
    )
    time.sleep(MINRATE / SECONDS)

    mined_block = Block.min_block(last_block,'age')

    assert mined_block.difficulty == 1

@pytest.fixture
def last_block():
    return Block.genesis()

@pytest.fixture
def block(last_block):
    return Block.min_block(last_block,'age')


def test_is_vaild_block(last_block,block):
    Block.is_valid_block(last_block,block)

def test_is_not_vaild_block(last_block,block):
    block.data = 'agecoder'
    with pytest.raises(Exception,match='The Block Does not Macth'):
        Block.is_valid_block(last_block,block)

def test_is_vaild_bad_proof_work(last_block,block):
    block.hash = 'ffffffff'

    with pytest.raises(Exception,match='The proof of works is not met'):
        Block.is_valid_block(last_block,block)


def test_is_vaild_bad_difficulty(last_block,block):
    block.difficulty = 10
    block.hash = f'{'0' * block.difficulty }111abc'

    with pytest.raises(Exception,match='he block difficulty must be adjusted by only 1'):
        Block.is_valid_block(last_block,block)

def  test_is_vaild_bad_block_hash_check(last_block,block):
    block.hash = '0000000000000000000000abc'

    with pytest.raises(Exception,match='The Block Does not Macth'):
        Block.is_valid_block(last_block,block)