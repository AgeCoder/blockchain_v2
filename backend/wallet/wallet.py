import json
from uuid import uuid4 as v4
from backend.config import STARTING_BALANCE
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes , serialization 
from cryptography.hazmat.primitives.asymmetric.utils import ( encode_dss_signature, decode_dss_signature) 
from cryptography.exceptions import InvalidSignature


class Wallet:

    def __init__(self,blockchain=None,private_key=None):
        self.blockchain = blockchain
        self.address = str(v4())[0:8]
        self.private_key = private_key or ec.generate_private_key(
            ec.SECP256K1(),
            default_backend()
        )
        self.public_key = self.private_key.public_key()
        self.serialize_public_key()
        self.private_key_s = self.serialize_private_key()
        

    def sign(self,data):
        return decode_dss_signature(self.private_key.sign(
            json.dumps(data).encode('utf-8'),
            ec.ECDSA(hashes.SHA256())
            )
        )

    @property
    def balance(self):
        return self.calculate_balance(self.blockchain,self.address)

    def serialize_public_key(self):
        self.public_key = self.public_key.public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')

    def serialize_private_key(self):
        """
        Serialize the private key to PEM format string.
        
        Returns:
            str: PEM formatted private key as string
        """
        try:
            return self.private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            ).decode('utf-8')
        except Exception as e:
            raise ValueError(f"Failed to serialize private key: {str(e)}")

    def deserialize_private_key(self, pem_key: str):
        """
        Deserialize a PEM formatted private key string back to an EC key object.
        
        Args:
            pem_key (str): PEM formatted private key string
            
        Returns:
            EllipticCurvePrivateKey: The deserialized private key
        """
        try:
            return serialization.load_pem_private_key(
                pem_key.encode('utf-8'),
                password=None,
                backend=default_backend()
            )
        except Exception as e:
            raise ValueError(f"Failed to deserialize private key: {str(e)}")
        
    
    @staticmethod
    def verify(public_key,data,signature):

        deserialized_public_key = serialization.load_pem_public_key(
            public_key.encode('utf-8'),
            default_backend
        )
        (r,s) = signature
        try:    
            deserialized_public_key.verify(
            encode_dss_signature(r,s),
            json.dumps(data).encode('utf-8'),
            ec.ECDSA(hashes.SHA256())
            )
            return True
        except InvalidSignature as e:
            print(f'Invaild signature {e}' )
            return False
    
    @staticmethod
    def calculate_balance(blockchain,address):
        balance = STARTING_BALANCE

        if blockchain is None:
            return balance
        
        for block in blockchain.chain:
            for transaction in block.data:
                if transaction['input']['address'] == address:
                    balance = transaction['output'][address]
                elif address in transaction['output']:
                    balance += transaction['output'][address]

        return balance


def main():
    wallet = Wallet()
    # print(f'wallet : \n {wallet.__dict__}')
    data = { 'age' : 'agecoder'}
    signature =  wallet.sign(data)
    
    is_vaild = Wallet.verify(wallet.public_key,data,signature)
    print(is_vaild)

    should_be_invaild = Wallet.verify(Wallet().public_key,data,signature)
    print(should_be_invaild)

if __name__ == '__main__':
    main()