from Mydbms.file_system import FileManager
from Mydbms import utils
import numpy as np
from json import loads, dumps

def header_serialize(header: dict) -> np.ndarray:
    page = np.zeros(utils.PAGE_SIZE, dtype=np.uint8)
    data = dumps(header, ensure_ascii=False).encode('utf-8')
    page[:len(data)] = list(data)
    return page


class RM_Manager:
    
    def __init__(self, manager:FileManager):
        self.filemanager = manager

    def CreateFile(self, fileName, recordSize):
        self.filemanager.create_file(fileName)
        fileId = self.filemanager.open_file(fileName)
        
        total_size = utils.PAGE_SIZE-utils.RM_PAGEHEADER_SIZE
        recordNumPerPage = (total_size << 3) // (1 + (recordSize << 3)) + 1
        while ((recordNumPerPage + 7) >> 3) + recordNumPerPage * recordSize > total_size:
            recordNumPerPage -= 1
        
        header = {
            "recordSize" : recordSize,
            "recordNumPerPage": recordNumPerPage, 
            "recordNumber": 0,
            "pageNumber": 1,
            'bitmapSize': (recordNumPerPage + 7) >> 3,
            'next_vacancy_page': 0,
            'filename': str(fileName),
        }

        self.filemanager.new_page(fileId,header_serialize(header))
        self.filemanager.close_file(fileId)

    def RemoveFile(self, fileName):
        self.filemanager.remove_file(fileName)

    def OpenFile(self, fileName):
        return self.filemanager.open_file(fileName)

    def CloseFile(self,fileID):
        self.filemanager.close_file(fileID)

    


