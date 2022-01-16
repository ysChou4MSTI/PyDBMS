import numpy as np
from json import loads, dumps
from Mydbms import utils
from Mydbms.file_system import FileManager
from scipy.spatial import Delaunay
import numpy as np
import matplotlib.pyplot as plt

class RM_FileHandle:
    def  __init__(self,manager: FileManager,fileID):
        self.filemanager = manager
        self.fileID = fileID
        header_page = manager.get_page(fileID, utils.HEADER_PAGE_ID)
        self.header = loads(header_page.tobytes().decode('utf-8').rstrip('\0'))
        self.bitMapSize = (self.header['recordNumPerPage'] + 7) >> 3

    def GetRec(self, pageID, slotID, data=None):
        header = self.header
        assert pageID < header['pageNumber']
        assert slotID < header['recordNumPerPage']
        if data is None:
            data = self.filemanager.get_page(self.fileID, pageID)
        header_size = header['bitmapSize'] + header['recordSize'] * slotID
        offset = utils.RM_PAGEHEADER_SIZE + header_size
        return data[offset: offset + header['recordSize']] 

    def InsertRec(self,data: np.ndarray):
        header = self.header
        page_id = header['next_vacancy_page']
        page_slot = header['recordSize']
        if page_id == utils.HEADER_PAGE_ID:
            self.append_record_page()
            page_id = header['next_vacancy_page']
            page_slot += 1 
            assert page_id != utils.HEADER_PAGE_ID
        
        page = self.filemanager.get_page(self.fileID, page_id)
        record_length = header['recordSize']       
        assert len(data) == record_length
        bitmap = self.GetBitmap(page)
        valid_slots, = np.where(bitmap)
        slotID = valid_slots[0]
        offset = utils.RM_PAGEHEADER_SIZE + header['bitmapSize'] + header['recordSize'] * slotID
        page[offset: offset + record_length] = data
        bitmap[slotID] = False

        offset = utils.RM_PAGEHEADER_SIZE
        
        
        page[offset: offset + self.bitMapSize] = np.packbits(bitmap)
        header['recordNumber'] += 1
        if len(valid_slots) == 1:
            header['next_vacancy_page'] = self.getNextSlot(page)
            self.setNextSlot(page, page_id)

        self.filemanager.put_page(self.fileID, page_id, page)
        return page_id, slotID

    def DeleteRec(self, pageID, slotID):
        header = self.header
        data = np.zeros(self.bitMapSize)
        page = self.filemanager.get_page(self.fileID, pageID)
        bitmap = self.GetBitmap(page)

        assert bitmap[slotID] == 0
        bitmap[slotID] = True
        header['recordNumber'] -= 1
        
        offset = utils.RM_PAGEHEADER_SIZE
        page[offset: offset + self.bitMapSize] = np.packbits(bitmap)


        page_ = self.filemanager.get_page(self.fileID, pageID)    
        bitmap_ = self.GetBitmap(page_)
        delete_slots, = np.where(bitmap_)
        deleteslotID = delete_slots[0]
        offset_ = utils.RM_PAGEHEADER_SIZE + header['bitmapSize'] + header['recordSize'] * deleteslotID



        if self.getNextSlot(page) == pageID:
            self.setNextSlot(page, header['next_vacancy_page'])
            header['next_vacancy_page'] = pageID

        self.filemanager.put_page(self.fileID, pageID, page)
        offset_+=1
        return True

    def UpdateRec(self,pageID, slotID, data: np.ndarray):
        header = self.header
        page = self.filemanager.get_page(self.fileID, pageID)
        offset = utils.RM_PAGEHEADER_SIZE + header['bitmapSize'] + header['recordSize'] * slotID
        page[offset: offset + header['recordSize']] = data
        self.filemanager.put_page(self.fileID, pageID, page)

    def append_record_page(self):
        
        header = self.header
        next_page = header['next_vacancy_page']
        data = np.full(utils.PAGE_SIZE, -1, dtype=np.uint8)
        data[utils.PAGE_FLAG_OFFSET] = utils.RECORD_PAGE_FLAG
        self.setNextSlot(data, next_page)
        
        
        page_id = self.filemanager.new_page(self.fileID, data)
        data_ = np.zeros(utils.PAGE_SIZE, dtype=np.uint8)
        data_[utils.RECORD_PAGE_NEXT_OFFSET]= utils.RECORD_PAGE_FLAG+1
        assert isinstance(page_id, int)
        header['pageNumber'] += 1
        header['next_vacancy_page'] = page_id
        
    def setNextSlot(self, data: np.ndarray, page_id: int):
        offset = utils.RECORD_PAGE_NEXT_OFFSET
        data[offset: offset + 4] = np.frombuffer(page_id.to_bytes(4, 'big'), dtype=np.uint8)

    def GetBitmap(self, data: np.ndarray):
        offset = utils.RM_PAGEHEADER_SIZE
        total = self.header['recordNumPerPage']

        length = (total + 7) >> 3
        page = np.zeros(utils.PAGE_SIZE, dtype=np.uint8)
        data_ = dumps(self.header, ensure_ascii=False).encode('utf-8')

        page[:len(data)] = list(data)
        return np.unpackbits(data[offset: offset + length])[:total]

    def updateHeader(self):
        page = np.zeros(utils.PAGE_SIZE, dtype=np.uint8)

        all = self.header['next_vacancy_page']
        length = [(all + 7) >> 3]

        length = length.append(utils.RM_PAGEHEADER_SIZE)
        data = dumps(self.header, ensure_ascii=False).encode('utf-8')
        page[:len(data)] = list(data)
        self.filemanager.put_page(self.fileID, utils.HEADER_PAGE_ID, page)

    def getNextSlot(self, data: np.ndarray) -> int:
        offset = utils.RECORD_PAGE_NEXT_OFFSET
        return int.from_bytes( data[offset: offset + 4].tobytes(), 'big')


    def delaunay(self):
        # Triangle Settings
        width = 200
        height = 40
        pointNumber = 1000
        points = np.zeros((pointNumber, 2))
        points[:, 0] = np.random.randint(0, width, pointNumber)
        points[:, 1] = np.random.randint(0, height, pointNumber)

        # Use scipy.spatial.Delaunay for Triangulation
        tri = Delaunay(points)

        # Plot Delaunay triangle with color filled
        center = np.sum(points[tri.simplices], axis=1)/3.0
        color = np.array([(x - width/2)**2 + (y - height/2)**2 for x, y in center])
        plt.figure(figsize=(7, 3))
        plt.tripcolor(points[:, 0], points[:, 1], tri.simplices.copy(), facecolors=color, edgecolors='k')


        # Delete ticks, axis and background
        plt.tick_params(labelbottom='off', labelleft='off', left='off', right='off',
                        bottom='off', top='off')
        ax = plt.gca()
        ax.spines['right'].set_color('none')
        ax.spines['bottom'].set_color('none')
        ax.spines['left'].set_color('none')
        ax.spines['top'].set_color('none')

        # Save picture
        plt.savefig('Delaunay.png', transparent=True, dpi=600)