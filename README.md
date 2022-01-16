# PyDBMS
A single user CLI DBMS in python.

#### Usage

in directory PyDBMS, type python3 booter.py to launch the system.

Suppoerted SQL commands can be find in PyDBMS/SQL.g4,

For instance, to use a database with commands,

SQL: CREATE DATABASE db_name;  USE db_name: CREATE Table_name (fields...);

 to change settinngs for database tables, use 

ALTER TABLE tb_name ADD CONSTRAINT PRIMARY KEY (pkfield), 

ALTER TABLE tb_name ADD CONSTRAINT fk_name FOREIGN KEY (fk_field...) REFERENCE ref_table(ref_fields...)



#### Architecture

#### ![system](/Users/elliot0412/Desktop/fifth_grade/data_base/dbms/PyDBMS-master/Mydbms/pic/system.jpg)





#### 



