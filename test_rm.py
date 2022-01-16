from Mydbms.record_system import RM_FileHandle,RM_FileScan,RM_Manager
from Mydbms.file_system import FileManager
import numpy as np
import random
all = set()
fm = FileManager()
rm  = RM_Manager(fm)
rm.CreateFile("test1.txt",8)
fileID = rm.OpenFile("test1.txt")
rm.CreateFile("test2.txt",8)
fileID2 = rm.OpenFile("test2.txt")
rm_filehandle = RM_FileHandle(fm,fileID)
for i in range(100):
   data = np.full(8,i,dtype = np.uint8)
   pageID, slotID = rm_filehandle.InsertRec(data)
   all.add((pageID, slotID))
   
   #if i > 10 and random.randint(0,9)<3:
    #  trash = all.pop()
    #  rm_filehandle.DeleteRec(trash[0],trash[1])
      
   if i > 5 and random.randint(0,9)<7:
      trash = all.pop()
      data = np.full(8,-1,dtype = np.uint8)
      rm_filehandle.UpdateRec(trash[0],trash[1], data)
      all.add(trash)
   
   
   

rm_scan = RM_FileScan(rm_filehandle, fm)
for i in rm_scan:
   pid = i[0]
   sid = i[1]
   if (pid,sid) not in all:
      print("Failed")

   all.remove((pid,sid))
   print(i)
print(len(all))
rm.CloseFile(fileID) 
rm.CloseFile(fileID2) 


