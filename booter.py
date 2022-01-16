from Mydbms.manager_system import SM_Manager, SM_SystemVisitor
import numpy as np
from pathlib import Path

visitor = SM_SystemVisitor()
sys_manager = SM_Manager(visitor, Path("data"))  

sql = ''
while True:
    sql += ' ' + input()
    if sql.strip().lower() == 'quit':
        break
    if sql.endswith(';'):
        sys_manager.run(sql)
        sql = ''

sys_manager.CloseDB(sys_manager.using_db)
print("Exiting Database... \nBye")