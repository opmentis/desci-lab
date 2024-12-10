from opmentis import register_user

# Register as a miner
wallet_address = "your_wallet_address"
labid = "dbc00e29-721f-40e6-b073-ec627db90115"
role_type = "miner"
register_response = register_user(wallet_address, labid, role_type)
print("Registration Response:", register_response)
