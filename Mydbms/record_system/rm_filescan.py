from .rm_filehandle import RM_FileHandle
from Mydbms.file_system import FileManager
from Mydbms import utils
import numpy as np

class RM_FileScan:
    def __init__(self, filehandle: RM_FileHandle, filemanager: FileManager):
        self.filehandle = filehandle
        self.fileID = filehandle.fileID
        self.filemanager = filemanager
    def __iter__(self):
        return self.allrecords() 

    def allrecords(self):
        for page_id in range(1, self.filehandle.header['pageNumber']):
            page = self.filemanager.get_page(self.fileID,page_id)
            if page[utils.PAGE_FLAG_OFFSET] == utils.RECORD_PAGE_FLAG:
                filebitmap = self.filehandle.GetBitmap(page)
                slots = np.where(filebitmap == 0)
                for slot_id in slots[0]:
                    record_data = self.filehandle.GetRec(page_id, slot_id, page)
                    yield (page_id, slot_id, record_data)