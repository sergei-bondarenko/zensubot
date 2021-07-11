from database import db_query
import time

print('Clean_plus_data started')
time.sleep(60)
db_query("delete from plus_data where chat_id = -1001211284566;", False)
print('Clean_plus_data ended')

