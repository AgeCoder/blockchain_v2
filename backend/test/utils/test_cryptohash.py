from backend.utils.cryptohash import crypto_hash

def test_crypto_hash():
    assert crypto_hash(1,[2],'3') == crypto_hash([2],1,'3')
    assert crypto_hash('foo') == 'b2213295d564916f89a6a42455567c87c3f480fcd7a1c15e220f17d7169a790b'

