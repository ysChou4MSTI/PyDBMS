from Mydbms.antlr_parser.SQLParser import SQLParser
from Mydbms.antlr_parser.SQLVisitor import SQLVisitor
from .sm_manager import SM_Manager
from antlr4 import ParserRuleContext

from prettytable import PrettyTable
def to_str(s):
    if isinstance(s, ParserRuleContext):
        s = s.getText()
    return str(s)

from .sm_meta import ColumnInfo, TableInfo

class Query_Response:
    def __init__(self, headers=None, data=None):
        if headers and not isinstance(headers, (list, tuple)):
            headers = (headers, )
        if data and not isinstance(data[0], (list, tuple)):
            data = tuple((each, ) for each in data)
        self._headers = headers
        self._data = data
        #print(data)

class Printer:
    class TablePrinter(PrettyTable):
        def _format_value(self, field, value):
            return 'NULL' if value is None else super()._format_value(field, value)


    def Print(self, result):
        table = self.TablePrinter()
        table.field_names = result._headers
        table.add_rows(result._data)
        if len(result._data):
            print(table.get_string())
        else:
            print('Empty set')
        print()

class SM_SystemVisitor(SQLVisitor):
    def __init__(self, manager = None):
        super().__init__()
        self.manager: SM_Manager = manager
        self.printer = Printer()
        
    def visitProgram(self, ctx: SQLParser.ProgramContext):
        for statement in ctx.statement():
            result = statement.accept(self)

    def visitShow_dbs(self, ctx: SQLParser.Show_dbsContext):
        print('databases: ' + ', '.join(tuple(self.manager.dbs)))
   

    def visitCreate_db(self, ctx: SQLParser.Create_dbContext):
        return self.manager.CreateDB(str(ctx.Identifier()))

    def visitDrop_db(self, ctx: SQLParser.Drop_dbContext):
        return self.manager.DropDB(str(ctx.Identifier()))

    def visitUse_db(self, ctx: SQLParser.Use_dbContext):
        print("Using database: "+ str(ctx.Identifier()))
        return self.manager.UseDB(str(ctx.Identifier()))

    

    def visitCreate_table(self, ctx:SQLParser.Create_tableContext):
        table_name = str(ctx.Identifier())
        columns, foreign_keys, primary = ctx.field_list().accept(self)
        self.manager.CreateTable(table_name,TableInfo(table_name,columns))
        
        for col_name in foreign_keys.keys():
            self.manager.SetForeignKey(table_name,col_name,(foreign_keys[col_name]))
            self.manager.AddForeignKey(table_name,col_name,foreign_keys[col_name])
        if primary:
            self.manager.AddPrimaryKey(table_name,primary)

    def visitField_list(self, ctx: SQLParser.Field_listContext):
        column_map = []
        foreign_key = {}
        primary_key = None
        for field in ctx.field():
            if isinstance(field, SQLParser.Normal_fieldContext):
                column_map.append(field.accept(self))
            if isinstance(field, SQLParser.Foreign_key_fieldContext):
                f_list = field.accept(self)
                if f_list[0] in foreign_key:
                    print("Error: Foreign key duplicated")
                    return
                foreign_key[f_list[0]] = f_list[1], f_list[2]
            
            if isinstance(field, SQLParser.Primary_key_fieldContext):
                pk_name = field.accept(self)
                if primary_key:
                     print("Error: Primary key more than one")
                     return

                primary_key = pk_name
                
        return column_map,foreign_key,primary_key

    def visitNormal_field(self, ctx: SQLParser.Normal_fieldContext):
        type, size = ctx.type_().accept(self)
        name = str(ctx.Identifier())
        isNull = True if (str(ctx.getChild(2)))!="NOT" else False
        default= ctx.value().accept(self)if ctx.value() else None
        
        return ColumnInfo(name, type, size, isNull, default)

    def visitForeign_key_field(self, ctx: SQLParser.Foreign_key_fieldContext):
        return [str(i) for i in ctx.Identifier()]

    def visitPrimary_key_field(self, ctx: SQLParser.Primary_key_fieldContext):
        return ctx.identifiers().accept(self)

    def visitIdentifiers(self, ctx: SQLParser.IdentifiersContext):
        return [str(i) for i in ctx.Identifier()]

    def visitType_(self, ctx: SQLParser.Type_Context):
        size = int(str(ctx.Integer())) if ctx.Integer() else 0
        return str(ctx.getChild(0)), size
        
    def visitDrop_table(self, ctx: SQLParser.Drop_tableContext):
        return self.manager.DropTable(str(ctx.Identifier()))
    
    def visitShow_tables(self, ctx: SQLParser.Show_tablesContext):
        return self.manager.ShowTables()

    def visitDescribe_table(self, ctx: SQLParser.Describe_tableContext):
        
        table = str(ctx.Identifier())
        header, data, pri, foreign = self.manager.DescTable(table)
        self.printer.Print(Query_Response(header, data))
        if len(pri):
            print(f"PRIMARY KEY {tuple(pri)};")
        if len(foreign.keys()):
            for k,v in foreign.items():
                if k == v[0]:
                    print(f"FOREIGN KEY ({v[0]}) REFERENCES {v[1][0]}({v[1][1]})")
                else:
                    print(f"FOREIGN KEY {k}{v[0]} REFERENCES {v[1][0]}({v[1][1]})")
        print()

    def visitAlter_table_add(self, ctx: SQLParser.Alter_table_addContext):
        table_name = str(ctx.Identifier())
        if isinstance(ctx.field(),SQLParser.Normal_fieldContext):
            col: ColumnInfo = ctx.field().accept(self)
            #header, data = self.manager.AddColumn(table_name, col)
            self.manager.AddColumn(table_name, col)
            #self.printer.Print(Query_Response(header, data))
        else:
            print("Error: Alter table add not normal field")

        

    def visitAlter_table_drop(self, ctx: SQLParser.Alter_table_dropContext):
        table_name = str(ctx.Identifier(0))
        col_name = str(ctx.Identifier(1))
        #header, data = self.manager.DropColumn(table_name,col_name)
        self.manager.DropColumn(table_name,col_name)
        #self.printer.Print(Query_Response(header, data))

    def visitAlter_table_rename(self, ctx: SQLParser.Alter_table_renameContext):
        old_table = str(ctx.Identifier(0))
        new_table = str(ctx.Identifier(1))
        self.manager.RenameTable(old_table,new_table)


    def visitAlter_table_add_pk(self, ctx: SQLParser.Alter_table_add_pkContext):
        tablename = str(ctx.Identifier(0))
        prikey = ctx.identifiers().accept(self)
        self.manager.AddPrimaryKey(tablename,prikey)
    
    def visitAlter_table_drop_pk(self, ctx: SQLParser.Alter_table_drop_pkContext):
        tablename = str(ctx.Identifier())
        self.manager.DropPrimaryKey(tablename)

    def visitAlter_table_add_foreign_key(self, ctx: SQLParser.Alter_table_add_foreign_keyContext):
        tablename = str(ctx.Identifier(0))
        foreign_name = str(ctx.Identifier(1))
        ref_tablename = str(ctx.Identifier(2))
        col_list = ctx.identifiers(0).accept(self)
        ref_col_list = ctx.identifiers(1).accept(self)
        if len(col_list) != len(ref_col_list):
            print('Error: key field num not equal')
            return
        self.manager.SetForeignKey(tablename,tuple(col_list),(ref_tablename, ref_col_list),foreign_name)
        for i in range(len(col_list)):
            self.manager.AddForeignKey(tablename, col_list[i],(ref_tablename, ref_col_list[i]), foreign_name)

    def visitAlter_table_drop_foreign_key(self, ctx: SQLParser.Alter_table_drop_foreign_keyContext):
        tablename = str(ctx.Identifier(0))
        foreign_name = str(ctx.Identifier(1))

        self.manager.DropForeignKey(tablename, foreign_name)

    def visitInsert_into_table(self, ctx: SQLParser.Insert_into_tableContext):
        tablename = str(ctx.Identifier())
        
        value_lists = ctx.value_lists().accept(self)
       
        for value_list in value_lists:
            self.manager.InsertRecord(tablename, value_list)
        #INSERT INTO nation VALUES (99,'Americas',0,'nothing left');

    def visitDelete_from_table(self, ctx: SQLParser.Delete_from_tableContext):
        table_name = str(ctx.getChild(2))
        conditions = ctx.where_and_clause().accept(self)
         #Eprint(conditions)
        self.manager.DeleteRecords(table_name, conditions)
        #DELETE FROM nation WHERE nation.n_nationkey=99;

    def visitUpdate_table(self, ctx: SQLParser.Update_tableContext):
        table_name = str(ctx.getChild(1))
        conditions = ctx.where_and_clause().accept(self)
        newValueMap = ctx.set_clause().accept(self)
        #print(table_name)
        #print(conditions)
        #for k,v in newValueMap.items():
            #print(k,v)
        self.manager.UpdateRecords(table_name,conditions,newValueMap)
        #UPDATE people SET p_nationkey=999 WHERE people.p_name='Eric';
        #UPDATE nation SET n_nationkey=999 WHERE nation.n_name='Americas';
    
    def visitSet_clause(self, ctx: SQLParser.Set_clauseContext):
        newValueMap = {}
        for identifier, value in zip(ctx.Identifier(), ctx.value()):
            newValueMap[str(identifier)] = value.accept(self)
        return newValueMap

    def visitSelect_table(self, ctx: SQLParser.Select_tableContext):
        table_names = ctx.identifiers().accept(self)
        conditions = ctx.where_and_clause().accept(self) if ctx.where_and_clause() else ()
        selectors = ctx.selectors().accept(self)
        #print(table_names,conditions,selectors)

        header, data = self.manager.SelectRecord(table_names,conditions,selectors)
        self.printer.Print(Query_Response(header, data))
    
    def visitSelectors(self, ctx: SQLParser.SelectorsContext):
        select_list = []
        if to_str(ctx.getChild(0)) == '*':
            return "*"
        for field in ctx.selector():
            select_list.append(field.accept(self))
        return tuple(select_list)
    
    def visitSelector(self, ctx: SQLParser.SelectorContext):
        table_name, column_name = ctx.column().accept(self)
        return [table_name,column_name]
    def visitWhere_and_clause(self, ctx: SQLParser.Where_and_clauseContext):
        cond_list = []
        for c in ctx.where_clause():
            cond_list.append(c.accept(self))
        return tuple(cond_list)
    
    def visitWhere_operator_expression(self, ctx: SQLParser.Where_operator_expressionContext):
        table_name, column_name = ctx.column().accept(self)
        
        operate = ctx.operate().accept(self)
        value = ctx.expression().accept(self)
        return [table_name,column_name, operate,value ]
        
    def visitOperate(self, ctx: SQLParser.OperateContext):
        return ctx.getText()
    
    
    def visitColumn(self, ctx: SQLParser.ColumnContext):
        
        return str(ctx.Identifier(0)), str(ctx.Identifier(1))
        
    
    def visitValue_lists(self, ctx: SQLParser.Value_listsContext):
        vlist = []
        for v in ctx.value_list():
            vlist.append(v.accept(self))
        return tuple(vlist)
       
    
    def visitValue_list(self, ctx: SQLParser.Value_listContext):
        vlist = []
        for vv in ctx.value():
            vlist.append(vv.accept(self))
        return tuple(vlist)
        
    
    def visitValue(self, ctx: SQLParser.ValueContext):
        text = ctx.getText()
        if ctx.Integer():
            return int(text)
        if ctx.Float():
            return float(text)
        if ctx.String():  # 1:-1 to remove "'" at begin and end
            return text[1:-1]
        if ctx.Null():
            return None
        
        
    #INSERT INTO nation VALUES (0,'America',0, 'nothing left');

    def visitLoad_data(self, ctx: SQLParser.Load_dataContext):
        file_name = str(ctx.String())
        table_name = str(ctx.Identifier())

        self.manager.LoadData(file_name,table_name)

    def visitStore_data(self, ctx: SQLParser.Store_dataContext):
        file_name = str(ctx.String())
        table_name = str(ctx.Identifier())

        self.manager.StoreData(file_name,table_name)

    def visitAlter_add_index(self, ctx: SQLParser.Alter_add_indexContext):
        print("Sorry, Index Module is not implemented")
        pass

    def visitAlter_drop_index(self, ctx: SQLParser.Alter_drop_indexContext):
        print("Sorry, Index Module is not implemented")
        pass

