from opmentis import request_reward_payment, check_user_balance

wallet_address = "wallet_address"
labid = "dbc00e29-721f-40e6-b073-ec627db90115"


# Request payment
request_amount = 0 #enter your amount
print(request_reward_payment(labid, wallet_address, request_amount))

# Check balance
print(check_user_balance(labid, wallet_address))
