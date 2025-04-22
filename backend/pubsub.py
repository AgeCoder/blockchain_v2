# import time

# from pubnub.pubnub import PubNub
# from pubnub.pnconfiguration import PNConfiguration
# from pubnub.callbacks import SubscribeCallback
# from backend.blockchain.block import Block
# from backend.wallet.transaction import Transaction

# pnconfig = PNConfiguration()
# pnconfig.subscribe_key = 'sub-c-5bcdbc2e-110f-400e-85da-67744a63e16c'
# pnconfig.publish_key = 'pub-c-3da67840-7df3-4489-80d9-9bf641b3886e'
# pnconfig.uuid = "myUniqueUUID"  
# pnconfig.daemon = True

# pubnub = PubNub(pnconfig)


# CHANNELS= {
#     'TEST' : 'TEST',
#     'BLOCK' : 'BLOCK',
#     'TRANSACTION' : 'TRANSACTION'
# }

# class Listener(SubscribeCallback):

#     def __init__(self, blockchain,transaction_pool):
#         self.blockchain = blockchain
#         self.transaction_pool = transaction_pool
        
#     def message(self, pubnub, message):
#         # print(f"📡 Received message on channel {message.channel}")
#         # print(f"🔍 Raw message: {message.message}")

#         if message.channel == CHANNELS['BLOCK']:
#             try:
#                 block = Block.from_json(message.message)
#                 # print("📦 Parsed Block:", block)

#                 last_block = self.blockchain.chain[-1]

#                 if block.hash == last_block.hash:
#                     print("⛔ Duplicate block received. Skipping replacement.")
#                     return

#                 potential_chain = self.blockchain.chain[:]
#                 potential_chain.append(block)

#                 self.blockchain.replace_chain(potential_chain)
#                 self.transaction_pool.clear_blockchain_transactions(self.blockchain)
#                 print("✅ Blockchain replaced successfully!")
#             except Exception as e:
#                 print(f"⚠️ Failed to replace chain: {e}")
        
#         elif message.channel == CHANNELS['TRANSACTION']:
#             # print(message)
#             transaction = Transaction.from_json(message.message)
#             self.transaction_pool.set_transaction(transaction)
#             print(f'\n The new transaction was added to transaction pool')



#     # def status(self, pubnub, status):
#     #     print(f"[STATUS] {status.category}")



# class PubSub:

#     def __init__(self,blockchain,transaction_pool):
#         self.pubnub = PubNub(pnconfig)
#         self.pubnub.subscribe().channels(list(CHANNELS.values())).execute()
#         self.pubnub.add_listener(Listener(blockchain,transaction_pool))

#     def publish(self,channel,message):
#         self.pubnub.publish().channel(channel).message(message).sync()

#     def broadcast_block(self,block):
#         self.publish(CHANNELS['BLOCK'],block.to_json())

#     def broadcast_transaction(self,transaction):
#         self.publish(CHANNELS['TRANSACTION'],transaction.to_json())

# def main():
#    pubnub = PubSub()
#    time.sleep(1)  
#    pubnub.publish(CHANNELS['TEST'],{'hello': 'world'})

# if __name__ == '__main__':
#     main()
