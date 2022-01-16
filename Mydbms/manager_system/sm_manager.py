
from antlr4 import InputStream, CommonTokenStream
from antlr4.error.Errors import ParseCancellationException
from antlr4.error.ErrorListener import ErrorListener
from copy import deepcopy

from Mydbms.record_system import RM_FileHandle,RM_FileScan,RM_Manager
from Mydbms.file_system import FileManager
from pathlib import Path
from Mydbms.antlr_parser import SQLLexer, SQLParser

from .sm_meta import SM_Meta, TableInfo, ColumnInfo
import csv

import pickle
import os

class SM_Manager:

    def __init__(self,visitor, base_path: Path):
        self.filemanager = FileManager()
        self.recordmanager  = RM_Manager(self.filemanager)
        self._base_path = base_path
        base_path.mkdir(exist_ok=True, parents=True)
        self.dbs = {path.name for path in base_path.iterdir()}
        self.dbs.remove(".DS_Store")

        self.db_meta = None
        self.using_db = None
        
        self.visitor = visitor
        self.visitor.manager = self


    def run(self, sql):
        input_stream = InputStream(sql)
        lexer = SQLLexer(input_stream)
        tokens = CommonTokenStream(lexer)
        parser = SQLParser(tokens)
        tree = parser.program()
        
        return self.visitor.visit(tree)

    def CreateDB(self, name: str):
        if name in self.dbs:
            print("Database "+name +" already exists")
            return
        self.db_meta = SM_Meta(name,[])
        db_path = self._base_path / name
        db_path.mkdir(parents=True)
        self.dbs.add(name)

        outfile = open(db_path / (name + ".meta"), "wb")
        pickle.dump(self.db_meta, outfile)
        outfile.close()
        

        
    def DropDB(self, name: str):
        db_path = self._base_path / name
        for each in db_path.iterdir():
            each.unlink()
        db_path.rmdir()
        self.dbs.remove(name)

        

    def UseDB(self,name):
        if self.using_db != None:
            self.CloseDB(self.using_db)

        db_path = self._base_path / name
        self.using_db = name
        
        infile = open(db_path / (name + ".meta"), 'rb')
        self.db_meta = pickle.load(infile)
        infile.close()


    def CloseDB(self,name):
        db_path = self._base_path / name

        outfile = open(db_path / (name + ".meta"), "wb")
        pickle.dump(self.db_meta, outfile)
       
        outfile.close()

        print("Database: "+name+" closed")

    def CreateTable(self, table_name, table: TableInfo):
        #CREATE TABLE nation( n_nationkey INT NOT NULL, n_name VARCHAR(25) NOT NULL, n_regionkey INT NOT NULL, n_comment VARCHAR(152), PRIMARY KEY ( n_nationkey ));
        #CREATE TABLE jobs( j_nationkey INT NOT NULL, j_name VARCHAR(25) NOT NULL, j_salary INT NOT NULL, PRIMARY KEY ( j_name, j_salary ));
        #CREATE TABLE people( n_name VARCHAR(25) NOT NULL, p_name VARCHAR(25) NOT NULL, p_age INT NOT NULL, p_nationkey INT NOT NULL, FOREIGN KEY (p_nationkey ) REFERENCES nation ( n_nationkey ));
        #CREATE TABLE hobbbies( h_name VARCHAR(25) NOT NULL, p_name VARCHAR(25) NOT NULL, p_age INT NOT NULL, h_level FLOAT NOT NULL);
        #INSERT INTO jobs VALUES(0,'scientist',1000);
        #INSERT INTO jobs VALUES(0,'doctor',100);
        #INSERT INTO hobbbies VALUES('kkk','fufufu',1000,122222);
        if self.using_db == None:
            print("Error: No using database for CreateTable")
            return

        self.db_meta._tbMap[table_name] = table
        record_size = table.total_size
        #print(record_size)
        table_path = str(self._base_path / self.using_db / table_name) + '.table'
        self.recordmanager.CreateFile(table_path,record_size)

        db_path = self._base_path / self.using_db
        outfile = open(db_path / (self.using_db + ".meta"), "wb")
        pickle.dump(self.db_meta, outfile)
        outfile.close()
       


    def DropTable(self, table_name):
        if self.using_db == None:
            print("Error: No using database for DropTable")
            return
        if table_name not in self.db_meta._tbMap.keys():
            print("Error: Drop table not in Databse: "+ self.using_db)
            return
        
        self.db_meta._tbMap.pop(table_name)
        table_path = str(self._base_path / self.using_db / table_name) + '.table'
        self.recordmanager.RemoveFile(table_path)
        db_path = self._base_path / self.using_db
        outfile = open(db_path / (self.using_db + ".meta"), "wb")
        pickle.dump(self.db_meta, outfile)
        outfile.close()


    def ShowTables(self):
        if self.using_db == None:
            print("Error: No using database for ShowTable")
            return
        if len(self.db_meta._tbMap.keys())==0:
            print("This is an empty database")
            return
        for i in self.db_meta._tbMap.keys():
            print(i)

    def DescTable(self,table_name):
        
        if self.using_db == None:
            print("Error: No using database for DescTable")
            return
        if table_name not in self.db_meta._tbMap.keys():
            print("Error: Table "+table_name+" not exist")
            return

        header = ('Field', 'Type', 'Null',  'Default')
        data = self.db_meta._tbMap[table_name].describe()
       
        return header,data,self.db_meta._tbMap[table_name].primary, self.db_meta._tbMap[table_name].foreign_map

    def AddPrimaryKey(self,table_name, primary: list):
        #ALTER TABLE nation ADD CONSTRAINT pk_name PRIMARY KEY (n_name,n_nationkey);
        #ALTER TABLE people ADD CONSTRAINT pk_name PRIMARY KEY (p_career);
        #print(primary)
        cols_name = self.db_meta._tbMap[table_name].column_map.keys()
        
        for i in primary:
            if i not in cols_name:
                print("Error: primary key field not valid")
                return
        self.db_meta._tbMap[table_name].primary = primary
        
        
        for col in primary:
            self.CreateIndex(table_name+'.'+col, table_name, col)
                
    def DropPrimaryKey(self, table_name):
        primary = self.db_meta._tbMap[table_name].primary 
        self.db_meta._tbMap[table_name].primary = []
        for col in primary:
            self.DropIndex(table_name+'.'+col)

    def SetForeignKey(self, table_name, col, reference, foreign_name= None):
        if foreign_name == None:
            self.db_meta._tbMap[table_name].foreign_map[col] = [col,reference]
        else:
            self.db_meta._tbMap[table_name].foreign_map[foreign_name] = [col,reference]

    def AddForeignKey(self, table_name, col, reference, foreign_name = None):
        # ALTER TABLE people ADD CONSTRAINT fk_name FOREIGN KEY (p_name,p_age) REFERENCES jobs (j_name,j_salary);
        
        if reference[0] not in self.db_meta._tbMap:
            print("Error: reference table not exist")
            return
        ref_primkey = self.db_meta._tbMap[reference[0]].primary
        
        if reference[1] not in ref_primkey:
            print("Error: foreign key refered is not a primary key")
            return
        
        self.db_meta._tbMap[table_name].foreign[col] = reference # ref_table, col name
        #self.db_meta._tbMap[table_name].foreign_name = foreign_name
        
        if col not in self.db_meta._tbMap[table_name].indexes.keys():
            self.CreateIndex(table_name+'.'+col, table_name, col)
           

    def DropForeignKey(self, table_name, foreign_name=None):
        #ALTER TABLE people DROP FOREIGN KEY fk_name;
        if foreign_name not in self.db_meta._tbMap[table_name].foreign_map:
            print(f'Error: foreign key name not match {foreign_name}for table {table_name}')
            return 
        cols = [col for col in self.db_meta._tbMap[table_name].foreign_map[foreign_name][0]]

        for c in cols:
            self.db_meta._tbMap[table_name].foreign.pop(c)

        self.db_meta._tbMap[table_name].foreign_map.pop(foreign_name)
        #self.DropIndex(table_name+'.'+col)
        

    def InsertRecord(self,table_name, attr_list: list):
        table_path = str(self._base_path / self.using_db / table_name) + '.table'
        fileID = self.recordmanager.OpenFile(table_path)
        rm_handle = RM_FileHandle(self.filemanager,fileID)

        table = self.db_meta._tbMap[table_name]
     
        data = table.build_record(attr_list)
        value_list = table.load_record(data)
        #ALTER TABLE nation ADD CONSTRAINT pk_name PRIMARY KEY (n_name,n_nationkey);
        #INSERT INTO nation VALUES (123,123,0, 'nothing left');
        #INSERT INTO people VALUES ('Taiwan','Eric',23, 666);
        if not self.InsertPKeyCollide(table_name,value_list,rm_handle) and not self.InsertFKeyConstraint(table_name,value_list):   
            rm_handle.InsertRec(data)
            print("Record Inserted!") 
          

        rm_handle.updateHeader()
        self.recordmanager.CloseFile(fileID)

    def InsertPKeyCollide(self,table_name,value_list,rm_handle):
        
        table = self.db_meta._tbMap[table_name]
        pkey= {}
        if len(table.primary) == 0:
            return False
        for c_name in table.primary:
            pkey[c_name] = value_list[table._colindex[c_name]]
        
        rm_scan = RM_FileScan(rm_handle, self.filemanager)
        records = []

        #for record in rm_scan:
          #  rec_values = table.load_record(record[2])
           # print(rec_values)
        #INSERT INTO nation VALUES (0,'Taiwan',0, 'nothing left');

        #No index, brute through the table 
        for record in rm_scan:
            conflicted = 0
            rec_values = table.load_record(record[2])
            for col_name, value in pkey.items():
                if value == rec_values[table._colindex[col_name]]:
                    conflicted +=1
            if conflicted == len(pkey):
                records.append(record)
        assert(len(records)<=1), f"Error: Table {table_name} already has conflicted primary key"
    
        if records:
            conflict_val  = table.load_record(records[0][2])
            print(f"Error: Table {table_name} conflicted records {value_list} and {conflict_val} with same pk {pkey.values()} ")
            return True
        return False


    def InsertFKeyConstraint(self,table_name,value_list):
        kid_table = self.db_meta._tbMap[table_name]
        if len(kid_table.foreign) == 0:
            return False
        #self.db_meta._tbMap[table_name].foreign[col] = reference # ref_table, col name

        for col_name in kid_table.foreign:
            foreign_table_name = kid_table.foreign[col_name][0]
            foreign_table = self.db_meta._tbMap[foreign_table_name]
            foreign_table_path = str(self._base_path / self.using_db / foreign_table_name) + '.table'
            foreign_fileID = self.recordmanager.OpenFile(foreign_table_path)
            foreign_rm_handle = RM_FileHandle(self.filemanager,foreign_fileID)
            foreign_rm_scan = RM_FileScan(foreign_rm_handle, self.filemanager)
            val = value_list[kid_table._colindex[col_name]]
            
            foreign_column_name = kid_table.foreign[col_name][1]
            
            results = 0
            for foreign_record in foreign_rm_scan:
                rec_values = foreign_table.load_record(foreign_record[2])
                #print(type(val),type(rec_values[foreign_table._colindex[foreign_column_name]]))
                if val == rec_values[foreign_table._colindex[foreign_column_name]]:
                    results += 1
            if results == 0:
                print(f"Error: Table {table_name} No Foreign Key for Colomn: {col_name} , {val} ")
                self.recordmanager.CloseFile(foreign_fileID)
                return True

            self.recordmanager.CloseFile(foreign_fileID)
        return False

        
    def DeleteRecords(self, table_name, conditions):
        table = self.db_meta._tbMap[table_name]
        table_path = str(self._base_path / self.using_db / table_name) + '.table'
        fileID = self.recordmanager.OpenFile(table_path)
        rm_handle = RM_FileHandle(self.filemanager,fileID)
        
        rm_scan = RM_FileScan(rm_handle, self.filemanager)
        hitrecords = []
        #find if table_name == conditions[0], table_name = cond[3][0]
        #print(conditions)
        newconditions = []
        for cond in conditions:
            if isinstance(cond[3], tuple):
                #print(cond[3][0],table._colindex[cond[1]],table._colindex[cond[3][1]])
                if table_name == cond[3][0] and table._colindex[cond[1]]!=None and table._colindex[cond[3][1]]!=None:
                    newconditions.append(cond)
            else:
                if table_name == cond[0] and table._colindex[cond[1]]!=None:
                    newconditions.append(cond)
        #print(newconditions)
        #DELETE FROM nation WHERE nation.n_nationkey>=0 AND nation.n_nationkey=nation.n_regionkey ;
        #for record in rm_scan:
            #rec_values = table.load_record(record[2])
            #print(rec_values)
        if len(newconditions) == 0:
            print("ERROR: Invalid Where clause for delete from")
            return
        for record in rm_scan:
            hit = 0
            rec_values = table.load_record(record[2])
            for cond in newconditions:
                if isinstance(cond[3], tuple):
                    hit = hit+1 if self.compareField(rec_values,table._colindex[cond[1]],cond[2],table._colindex[cond[3][1]]) else hit
                else:
                    hit = hit+1 if self.compareValue(rec_values,table._colindex[cond[1]],cond[2],cond[3]) else hit
            if hit == len(newconditions):
                hitrecords.append(record)

        for r in hitrecords:
            rm_handle.DeleteRec(r[0],r[1])
            print("Delete record: ",table.load_record(r[2]))
        
        rm_handle.updateHeader()
        self.recordmanager.CloseFile(fileID)
        

    def UpdateRecords(self,table_name, conditions: tuple, valueMap: dict):
        table = self.db_meta._tbMap[table_name]
        table_path = str(self._base_path / self.using_db / table_name) + '.table'
        fileID = self.recordmanager.OpenFile(table_path)
        rm_handle = RM_FileHandle(self.filemanager,fileID)

        rm_scan = RM_FileScan(rm_handle, self.filemanager)
        hitrecords = []
        hitvalues = []
        newconditions = []
        for cond in conditions:
            if isinstance(cond[3], tuple):
                #print(cond[3][0],table._colindex[cond[1]],table._colindex[cond[3][1]])
                if table_name == cond[3][0] and table._colindex[cond[1]]!=None and table._colindex[cond[3][1]]!=None:
                    newconditions.append(cond)
            else:
                if table_name == cond[0] and table._colindex[cond[1]]!=None:
                    newconditions.append(cond)
        #print(newconditions)   
        for record in rm_scan:
            
            hit = 0
            rec_values = table.load_record(record[2])
            #print(rec_values)
            for cond in newconditions:
                if isinstance(cond[3], tuple):
                    hit = hit+1 if self.compareField(rec_values,table._colindex[cond[1]],cond[2],table._colindex[cond[3][1]]) else hit
                else:
                    hit = hit+1 if self.compareValue(rec_values,table._colindex[cond[1]],cond[2],cond[3]) else hit
            if hit == len(newconditions):
                hitrecords.append(record)
                hitvalues.append(rec_values)
                #print(rec_values)
        
        for record, OldvVals in zip(hitrecords, hitvalues):
            NEWVals = list(OldvVals)
            for column_name, value in valueMap.items():
                index = table._colindex[column_name]
                if index!=None:
                    NEWVals[index] = value
            
            if not self.InsertPKeyCollide(table_name,NEWVals,rm_handle) and not self.InsertFKeyConstraint(table_name,NEWVals):   
                newdata = table.build_record(NEWVals)
                rm_handle.UpdateRec(record[0],record[1], newdata)
                print(f"Record Updated from {OldvVals} to : {NEWVals}")   

        rm_handle.updateHeader()
        self.recordmanager.CloseFile(fileID)


    def SelectRecord(self, table_names,conditions: tuple,selectors: tuple):
        if len(table_names) > 1:
            print("Sorry, queries from joining two tables are not supported")
            return
        table_name = table_names[0]
        table = self.db_meta._tbMap[table_names[0]]
        table_path = str(self._base_path / self.using_db / table_names[0]) + '.table'
        fileID = self.recordmanager.OpenFile(table_path)
        rm_handle = RM_FileHandle(self.filemanager,fileID)

        rm_scan = RM_FileScan(rm_handle, self.filemanager)
        hitrecords = []
        data = []
        newconditions = []
        for cond in conditions:
            if isinstance(cond[3], tuple):
                #print(cond[3][0],table._colindex[cond[1]],table._colindex[cond[3][1]])
                if table_name == cond[3][0] and table._colindex[cond[1]]!=None and table._colindex[cond[3][1]]!=None:
                    newconditions.append(cond)
            else:
                if table_name == cond[0] and table._colindex[cond[1]]!=None:
                    newconditions.append(cond)
        if len(newconditions) == 0:
            for record in rm_scan:
                rec_values = table.load_record(record[2])
                hitrecords.append(record)
                data.append(rec_values)
        else:
            for record in rm_scan:
                hit = 0
                rec_values = table.load_record(record[2])
                for cond in newconditions:
                    if isinstance(cond[3], tuple):
                        hit = hit+1 if self.compareField(rec_values,table._colindex[cond[1]],cond[2],table._colindex[cond[3][1]]) else hit
                    else:
                        hit = hit+1 if self.compareValue(rec_values,table._colindex[cond[1]],cond[2],cond[3]) else hit
                if hit == len(newconditions):
                    hitrecords.append(record)
                    data.append(rec_values)

        rm_handle.updateHeader()
        self.recordmanager.CloseFile(fileID)
        
        if selectors[0] == '*':
            return tuple(table.column_map.keys()),data
        else:
            def SliceFields(_row):
                return tuple(_row[each] for each in col_indexes)
            headers = tuple(selector[1] for selector in selectors)
            col_indexes = tuple(table._colindex[header] for header in headers)
            slicedata = tuple(map(SliceFields, data))
            return headers,slicedata

        #SELECT nation.n_nationkey,nation.n_comment  FROM nation WHERE nation.n_name = 'America';


    def AddColumn(self, table_name, col_info : ColumnInfo):
        #ALTER TABLE people ADD height INT NOT NULL;   
        if self.using_db == None:
            print("Error: No using database for AddColumn")
            return
        if col_info.name in self.db_meta._tbMap[table_name].column_map.keys():
            print(f'Error: Column {col_info.name} already exist')
            return 

        table = self.db_meta._tbMap[table_name]
        old_table = deepcopy(table)
        table.insert_column(col_info)
        #print(table.total_size)
        
        table_path = str(self._base_path / self.using_db / table_name) + '.table'
        fileID = self.recordmanager.OpenFile(table_path)
        rm_handle = RM_FileHandle(self.filemanager,fileID)

        new_table_path = str(self._base_path / self.using_db / table_name) + '.table_new'
        self.recordmanager.CreateFile(new_table_path, table.total_size)
        newfileID = self.recordmanager.OpenFile(new_table_path)
        new_rm_handle = RM_FileHandle(self.filemanager,newfileID)

        rm_scan = RM_FileScan(rm_handle, self.filemanager)
        
        #print_list = []
        #for i in range(10):
        #    attr_list = ["taiwan","eric",int(i)*10, "engineer"]
        #    ddata = old_table.build_record(attr_list)
        #    rm_handle.InsertRec(ddata)

        for record in rm_scan:
            value_list = list(old_table.load_record(record[2]))
            if col_info.default is not None:
                value_list.append(col_info.default)
            else:
                value_list.append(None)

            #print_list.append(value_list)

            data = table.build_record(value_list)
            
            new_rm_handle.InsertRec(data)

        rm_handle.updateHeader()
        new_rm_handle.updateHeader()
        self.recordmanager.CloseFile(fileID)
        self.recordmanager.CloseFile(newfileID)

        self.recordmanager.RemoveFile(table_path)
        os.rename(new_table_path, table_path)

        db_path = self._base_path / self.using_db
        outfile = open(db_path / (self.using_db + ".meta"), "wb")
        pickle.dump(self.db_meta, outfile)
        outfile.close()

        #header = tuple(table.column_map.keys())
        #return header, tuple(print_list)
        

    def DropColumn(self, table_name, col_name):
 
        #ALTER TABLE people DROP height
        if col_name  not in self.db_meta._tbMap[table_name].column_map.keys():
            print(f'Error: Column {col_name} not exist')
            return 
        table = self.db_meta._tbMap[table_name]
        index = table._colindex[col_name]
        old_table = deepcopy(table)

        table.remove_column(col_name)
        #print(table.total_size)

        table_path = str(self._base_path / self.using_db / table_name) + '.table'
        fileID = self.recordmanager.OpenFile(table_path)
        rm_handle = RM_FileHandle(self.filemanager,fileID)
        new_table_path = str(self._base_path / self.using_db / table_name) + '.table_new'
        self.recordmanager.CreateFile(new_table_path, table.total_size)
        newfileID = self.recordmanager.OpenFile(new_table_path)
        new_rm_handle = RM_FileHandle(self.filemanager,newfileID)
        rm_scan = RM_FileScan(rm_handle, self.filemanager)

        #print_list = []
        #for i in range(10):
          #  attr_list = ["taiwan","eric",int(i), "engineer", int(i)*10]
          #  ddata = old_table.build_record(attr_list)
          #  rm_handle.InsertRec(ddata)
            
        for record in rm_scan:
            
            value_list = list(old_table.load_record(record[2]))
            value_list.pop(index)
            data = table.build_record(value_list)
           # print(value_list)
            new_rm_handle.InsertRec(data)

       

        rm_handle.updateHeader()
        new_rm_handle.updateHeader()
        self.recordmanager.CloseFile(fileID)
        self.recordmanager.CloseFile(newfileID)
        os.rename(new_table_path, table_path)

        db_path = self._base_path / self.using_db
        outfile = open(db_path / (self.using_db + ".meta"), "wb")
        pickle.dump(self.db_meta, outfile)
        outfile.close()
        #header = tuple(table.column_map.keys())
        #return header, tuple(print_list)

    def RenameTable(self,oldname,newname):
        #ALTER TABLE people RENAME TO peoples;  
        self.db_meta._tbMap[oldname].name = newname
        self.db_meta._tbMap[newname] = self.db_meta._tbMap.pop(oldname)

    def LoadData(self,file_name,table_name):
        if table_name not in self.db_meta._tbMap:
            print("Error: target table not exist")
            return 
        table = self.db_meta._tbMap[table_name]
        cnt = 0
        with open('csv_files/'+file_name[1:-1], newline='\n',encoding='utf-8') as csvfile:
            rows = csv.reader(csvfile)
            for row in rows:
                attr_list = tuple(map(self.decoder, zip(row, table.type_list)))
                #print(attr_list)
                self.InsertRecord(table_name, attr_list)
        print("finish")
        
   #LOAD DATA INFILE 'customer.csv' INTO TABLE CUSTOMER;
    #LOAD DATA INFILE 'lineitem.csv' INTO TABLE LINEITEM;
    #LOAD DATA INFILE 'nation.csv' INTO TABLE NATION;
    #LOAD DATA INFILE 'orders.csv' INTO TABLE ORDERS;
    #LOAD DATA INFILE 'part.csv' INTO TABLE PART;
    #LOAD DATA INFILE 'partsupp.csv' INTO TABLE PARTSUPP;
    #LOAD DATA INFILE 'region.csv' INTO TABLE REGION;
    #LOAD DATA INFILE 'supplier.csv' INTO TABLE SUPPLIER;

   #STORE DATA OUTFILE 'test1.csv' FROM TABLE nation;     
    def StoreData(self,file_name,table_name):
        table = self.db_meta._tbMap[table_name]
        table_path = str(self._base_path / self.using_db / table_name) + '.table'
        fileID = self.recordmanager.OpenFile(table_path)
        rm_handle = RM_FileHandle(self.filemanager,fileID)

        rm_scan = RM_FileScan(rm_handle, self.filemanager)
        hitrecords = []
        data = []
        for record in rm_scan:
            rec_values = table.load_record(record[2])
            hitrecords.append(record)
            data.append(rec_values)

        with open('csv_files/'+file_name[1:-1], 'w', newline='\n') as csvfile:
            writer = csv.writer(csvfile)
            for row in data:
                writer.writerow(row)

        self.recordmanager.CloseFile(fileID)
    def CreateIndex(self,index_name, table_name, column_name): 
        pass

    def DropIndex(self,index_name):
        pass

    def compareValue(self, field, index, operator, value):
        if operator == '=':
            return field[index] == value
        if operator == '>':
            return  field is not None and field[index] > value
        if operator == '>=':
            return  field is not None and field[index] >= value
        if operator == '<':
            return  field is not None and field[index] < value
        if operator == '<=':
            return field is not None and field[index] <= value
        if operator == '<>':
            return  field[index] != value


    def compareField(self, field, index, operator, elseindex):
        if operator == '=':
            return field[index] == field[elseindex]
        if operator == '>':
            return  field[index] > field[elseindex]
        if operator == '>=':
            return field[index] >= field[elseindex]
        if operator == '<':
            return  field[index] < field[elseindex]
        if operator == '<=':
            return field[index] <= field[elseindex]
        if operator == '<>':
            return  field[index] != field[elseindex]

    def decoder(self, val_type_pair):
        val, type = val_type_pair
        if type == 'VARCHAR':
            return val.rstrip().lstrip()[1:-1]
        if type == 'INT':
            return int(val) if val else None
        if type == 'FLOAT':
            return float(val) if val else None
       
        