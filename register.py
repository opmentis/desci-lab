from opmentis import register_user

# Register as a miner
wallet_address = "your_wallet_address"
labid = "your_lab_id"
role_type = "miner"
register_response = register_user(wallet_address, labid, role_type)
print("Registration Response:", register_response)
