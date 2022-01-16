import struct
import numpy as np
from numbers import Number
from __future__ import annotations
import sys
NULL_VALUE = -1<<32

class ColumnInfo:
    def __init__(self,name_, type_, size_, isNull_ = False, default_=None) -> None:
        self.type = type_
        self.name = name_
        self.size = size_
        self.default = default_
        self.isNull = isNull_
    def get_size(self) -> int:
        if self.type == "INT":
            return 8
        elif self.type == "FLOAT":
            return 8
        elif self.type == "VARCHAR":
            return self.size + 1
    def print(self):
        print(self.name, self.type, self.size, self.isNull, self.default)




class TableInfo:
    def __init__(self, name, columns: list):
        self._name = name
        self.columns = columns
        self.foreign_map= {}
        self.primary = []
        self.foreign = {} # foreign 
        self.indexes = {} # col rootID
        self.size_list = []
        self.type_list = []
        self.column_map = {}
        self.total_size = 0
        self._colindex = {}
        self.updateTable()

    def updateTable(self):
        self.column_map = {col.name: col for col in self.columns}
        self.size_list = tuple(map(ColumnInfo.get_size, self.column_map.values()))
        self.type_list = tuple(map(lambda x: x.type, self.column_map.values()))
        self.total_size = sum(self.size_list)
        self._colindex = {col.name: i for i, col in enumerate(self.columns)}

    def describe(self):
        data = []
        for c  in self.columns:
            field = c.name
            type =  f'{c.type}{"(%d)" % c.get_size()}' 
            isnull = "YES" if c.isNull else "NO"
            key = ''
            if self.primary:
                key = "PRI" if c.name in self.primary else ""
            #print((self.foreign.keys()))
            if self.foreign.keys():
                if c.name in self.foreign.keys():
                    key = "MUL" if key == "PRI" else "FOR"           
            default = "NULL" if not c.default else c.default
            data.append([field, type, isnull, default])
        
        return tuple(data)

    def insert_column(self, column: ColumnInfo):
        if column.name not in self.column_map:
            self.columns.append(column)
            self.updateTable()
        else:
            print(f'Error: column {column.name} already exist')

    def remove_column(self, column_name):
        if column_name in self.column_map:
            self.columns = [column for column in self.columns if column.name != column_name]
            self.updateTable() 

        else:
            print(f'Error: cannot remove non exist column')
    
    def load_record(self, data):
        res = []
        pos = 0
        for size_, type_ in zip(self.size_list, self.type_list):
            
            res.append(self.deserialize(data[pos: pos + size_], type_))
            pos += size_
        assert pos == self.total_size
        return tuple(res)

    def deserialize(self, data: np.ndarray, type_):
        value = None
        
        if type_ == "VARCHAR":
            value = None if data[0] else data.tobytes()[1:].rstrip(b'\x00').decode('utf-8')
        elif type_ == "INT":
            value = struct.unpack('<q', data)[0]
        elif type_ == "FLOAT":
            value = struct.unpack('<d', data)[0]
        
        return None if value == NULL_VALUE else value

    def build_record(self,attr_list):
        
        assert(len(attr_list) == len(self.size_list))

        record_data = np.zeros(shape=self.total_size, dtype=np.uint8)
        pos = 0
        cnt = 0
        
        for size_, type_, value_ in zip(self.size_list, self.type_list, attr_list):
            if type_ == "VARCHAR":
                if value_ is None:
                    field_len = 1
                    bytes_ = (1, )
                else:
                    assert isinstance(value_, str), f"Error: field {self.columns[cnt].name} need to be a VARCHAR({size_ - 1}) "
                    bytes_ = (0,) + tuple(value_.encode())
                    field_len = len(bytes_)
                    assert(field_len <= size_)
                record_data[pos: pos + field_len] = bytes_
                record_data[pos + field_len: pos + size_] = 0
            else:
                data = None
                assert(type_ in ["INT","FLOAT"])
                if type_ == "INT":
                    if value_ is None:
                        value_ = NULL_VALUE 
                    
                    assert (isinstance(value_, int)) ,f"Error: field {self.columns[cnt].name} need to be a int "
                    #print("In build "+str(value_))
                    data = struct.pack('<q', value_)
                else:
                    if value_ is None:
                        value_ = NULL_VALUE
                    assert(isinstance(value_, Number)) ,f"Error: field{self.columns[cnt].name} need to be a float "
                    data =  struct.pack('<d', value_)

                record_data[pos: pos + size_] = list(data)
            pos += size_
            cnt+=1
        

        assert pos == self.total_size
        return record_data

    

class SM_Meta:
    def __init__(self, dbname, tables: list):
        self._DbName = dbname
        self._tbMap = {tb._name: tb for tb in tables}


class Bag:
    items: list[1]

    def __init__(self):
        self.items = []

    def printAllItemsDescription(self):
        for item in self.items:
            item.printDescription()


 
class Graph():
 
    def __init__(self, vertx):
        self.V = vertx
        self.graph = [[0 for column in range(vertx)]
                      for row in range(vertx)]
 
    def pSol(self, dist):
        print("Distance of vertex from source")
        for node in range(self.V):
            print(node, "t", dist[node])
 

    def minDistance(self, dist, sptSet):
 

        min = sys.maxsize
 

        for v in range(self.V):
            if dist[v] < min and sptSet[v] == False:
                min = dist[v]
                min_index = v
 
        return min_index
 

    def dijk(self, source):
 
        dist = [sys.maxsize] * self.V
        dist[source] = 0
        sptSet = [False] * self.V
 
        for cout in range(self.V):
 
            u = self.minDistance(dist, sptSet)
 
            sptSet[u] = True
 

            for v in range(self.V):
                if self.graph[u][v] > 0 and sptSet[v] == False and dist[v] > dist[u] + self.graph[u][v]:
                    dist[v] = dist[u] + self.graph[u][v]
        self.pSol(dist)

f = Graph(9)
f.graph = [[0, 4, 0, 0, 0, 0, 0, 8, 0],
           [4, 0, 8, 0, 0, 0, 0, 11, 0],
           [0, 8, 0, 7, 0, 4, 0, 0, 2],
           [0, 0, 7, 0, 9, 14, 0, 0, 0],
           [0, 0, 0, 9, 0, 10, 0, 0, 0],
           [0, 0, 4, 14, 10, 0, 2, 0, 0],
           [0, 0, 0, 0, 0, 2, 0, 1, 6],
           [8, 11, 0, 0, 0, 0, 1, 0, 7],
           [0, 0, 2, 0, 0, 0, 6, 7, 0]
           ]
 
f.dijk(0)