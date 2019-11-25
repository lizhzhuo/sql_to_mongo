#coding=utf-8
import sqlparse
import sqlparse.tokens as Token

def ddl_create(tokens):
    """ start-> database -> mongo                    example:CREATE DATABASE abc
              | table ->                             example:CREATE TABLE Persons(Id_P int,LastName varchar(255),FirstName varchar(255),Address varchar(255),City varchar(255))
              | index -> index_name -> on -> mongo   example:CREATE INDEX PersonIndex ON Person (LastName DESC, FirstName)

    """
    state = "start"
    mongo = ""
    # ===for create index===
    index_name = None

    for token in tokens:
        if token.is_whitespace: continue
        if state == "start" and token.ttype == Token.Keyword and token.value.upper() == "DATABASE":
            state = "database"
        if state == "start" and token.ttype == Token.Keyword and token.value.upper() == "TABLE":
            state = "collection"
        if state == "start" and token.ttype == Token.Keyword and token.value.upper() == "INDEX":
            state = "index"
        # ------------------------------------ create database ----------------------------------------------
        if state == "database" and isinstance(token, sqlparse.sql.Identifier):  # TODO:error handle
            mongo = "use %s" % token.value
            state = "finish"
            return mongo
        # ------------------------------------- create collection ----------------------------------------------
        if state == "collection" and isinstance(token,sqlparse.sql.Identifier):
            mongo = '''db.createCollection("%s")'''% token.value
            state = "finish"
            return mongo
        # ------------------------------------- create index ----------------------------------------------
        if state == "index" and isinstance(token, sqlparse.sql.Identifier):
            # print(token)
            index_name = token.get_real_name()
            state = "index_name"
        if state == "index_name" and token.ttype == Token.Keyword and token.value.upper() == "ON":
            state = "on"
        if state == "on" and isinstance(token, sqlparse.sql.Function):  # TODO:error handle
            collection = None
            columns = []
            for iden in token:
                if iden.is_whitespace: continue
                if isinstance(iden, sqlparse.sql.Identifier):
                    collection = iden.value
                else:
                    column = None
                    order = 1
                    column_name = None
                    for column in iden:
                        if column.ttype == Token.Punctuation and column.value != '(':  # 如果遇到符号则保存前面扫过的
                            columns.append({'column': column_name, 'order': order})
                            column = None
                            order = 1
                        else:
                            if isinstance(column, sqlparse.sql.Identifier):
                                column_name = column.value
                            elif column.ttype == Token.Keyword.Order:
                                if column.value.upper() == 'DESC':
                                    order = -1
            mongo = "db.%s.createIndex({" % collection
            i = 1
            # print(mongo)
            for each_index in columns:
                # print(each_index)
                if i != 1: mongo += ","
                mongo += '''"%s":%d''' % (each_index['column'], each_index['order'])
                i += 1
            mongo += '''},{"name","%s"})''' % index_name

            # print(mongo)
            state = "finish"
            return mongo

def ddl_drop(tokens):
    """ start -> database -> mongo  #  为了支持多个，返回list         example: DROP DATABASE db1,db2
               |  table -> mongo    #为了支持多个，返回list         example: DROP TABLE table1,table2
               |  index -> mongo    # 没做   ！因为plsql 的删除index没有指定表(DROP INDEX idx_name;)，所以不知道怎么改成Mongo，mongo需要指定collalation(db.collation.dropindex(index_name))
    """
    state = "start"
    mongo = ""

    for token in tokens:
        if token.is_whitespace: continue
        if state == "start" and token.ttype == Token.Keyword and token.value.upper() == "DATABASE":
            state = "database"
        if state == "start" and token.ttype == Token.Keyword and token.value.upper() == "TABLE":
            state = "table"
        if state == "start" and token.ttype == Token.Keyword and token.value.upper() == "INDEX":
            state = "index"

        if state=="database" and (isinstance(token,sqlparse.sql.Identifier) or isinstance(token,sqlparse.sql.IdentifierList)) :
            collections = []
            mongos = []
            if isinstance(token,sqlparse.sql.Identifier):
                collections.append(token.value)
            elif isinstance(token,sqlparse.sql.IdentifierList):
                for sub_token in token:
                    if isinstance(sub_token, sqlparse.sql.Identifier) :
                        collections.append(sub_token.value)
            for collection in collections:
                mongo = "use %s"%collection
                mongos.append(mongo)
                mongo = "db.dropDatabase()"
                mongos.append(mongo)
            return mongos
        if state=="table" and (isinstance(token,sqlparse.sql.Identifier) or isinstance(token,sqlparse.sql.IdentifierList)) :
            collections = []
            mongos = []
            if isinstance(token,sqlparse.sql.Identifier):
                collections.append(token.value)
            elif isinstance(token,sqlparse.sql.IdentifierList):
                for sub_token in token:
                    if isinstance(sub_token, sqlparse.sql.Identifier) :
                        collections.append(sub_token.value)
            for collection in collections:
                mongo="db.%s.drop()"%collection
                mongos.append(mongo)
            return mongos

        # TODO

def dml_insert(tokens):
    """ INSERT INTO TABLE (COLUMN...) VALUES (value...)
        start -> table(column) |-> values -> value -> mongo                example:INSERT  INTO Persons VALUES ('Gates', 'Bill', 'Xuanwumen 10', 'Beijing') #暂时没法做，需要考虑列名
                                                                        INSERT INTO Persons (LastName, Address) VALUES ('Wilson', 'Champs-Elysees')
        """
    state = "start"
    mongo = ""

    collection = None
    column_value = []

    for token in tokens:
        if token.is_whitespace: continue
        if state=="start" and token.ttype==Token.Keyword and token.value.upper()=="INTO":
            state = "table"
        if state =="table" and isinstance(token,sqlparse.sql.Function):
            for i in token :
                if isinstance(i,sqlparse.sql.Identifier):
                    collection = i.get_real_name()
                elif isinstance(i,sqlparse.sql.Parenthesis):
                    column_group = i.tokens[1]
                    for column in column_group:
                        if isinstance(column,sqlparse.sql.Identifier):
                            column_value.append({"column":column.get_real_name(),"value":None})
            state = "values"
        if state == "values" and token.ttype==Token.Keyword and token.value.upper()=="VALUES":
            state = "value"
        if state == "value" and isinstance(token,sqlparse.sql.Parenthesis):
            if isinstance(token,sqlparse.sql.Parenthesis):
                value_group = token.tokens[1]
                i = 0
                for value in value_group:
                    if value.ttype == Token.Literal.String.Single:
                        column_value[i]["value"]= value.value.strip("'")
                        i+=1
            # print(column_value)
            state = "finish"
        if state == "finish":
            mongo = '''db.%s.insert({'''%collection
            i=1
            for item in column_value:
                if i>1: mongo+=","
                mongo += '''"%s":"%s"'''%(item["column"],item["value"])
                i+=1
            mongo += '''})'''
            return mongo

def handle_where(operate,deep=0):
    """
        logic : factor and factor | factor or factor
        factor : column | (logic)
    """
    deep+=1
    left = None
    op = None
    right = None
    sub_mongo = ""
    if isinstance(operate,sqlparse.sql.Comparison):
        for i in range(len(operate.tokens)-1,-1,-1):
            if operate.tokens[i].is_whitespace: operate.tokens.pop(i)
        left = operate[0].value
        op = operate[1].value.upper()
        right = operate[2].value
        if op=="<":
            sub_mongo += '''"%s":{$lt:%s}'''%(left,right)
        elif op==">":
            sub_mongo += '''"%s":{$gt:%s}'''%(left,right)
        elif op=="=":
            sub_mongo += '''"%s":%s''' % (left, right)
        elif op=="<=":
            sub_mongo += '''"%s":{$lte:%s}''' % (left, right)
        elif op==">=":
            sub_mongo += '''"%s":{$gte:%s}''' % (left, right)
        elif op=="!=":
            sub_mongo += '''"%s":{$ne:%s}''' % (left, right)
        return sub_mongo
    else: # Parenthesis
        if len(operate)!=1:
            i=1
            for sub_operate in operate:

                if isinstance(sub_operate, sqlparse.sql.Parenthesis) or isinstance(sub_operate, sqlparse.sql.Comparison) or (
                                sub_operate.ttype == Token.Keyword and (sub_operate.value.upper() == "AND" or sub_operate.value.upper() == "OR")):
                    if i == 1:
                        left = sub_operate
                        i+=1
                    elif i == 2:
                        op = sub_operate
                        i+=1
                    elif i == 3:
                        right = sub_operate
                        i+=1
            # print(left)
            # print(op)
            # print(right)
            # return

            mongo_left = handle_where(left,deep)
            mongo_right = handle_where(right,deep)
            if op.value.upper() == "AND":
                sub_mongo += '''{%s,%s}'''%(mongo_left,mongo_right)
            elif op.value.upper() == "OR":
                if deep==1:
                    sub_mongo += '''{$or:[{%s},{%s}]}''' % (mongo_left, mongo_right)
                else :
                    sub_mongo += '''$or:[{%s},{%s}]''' % (mongo_left, mongo_right)
            return sub_mongo
        else:
            return "{"+handle_where(operate[0],deep)+"}"

def dml_select(tokens):
    """ start -> column -> from -> [where ->][order by] mongo                example:select id,cd from student where a<1 and b>2;  还未做其他
    """
    state = "start"
    mongo = ""

    # ===for select ====
    columns = []
    tables = []
    has_where = False
    where_mongo = None
    where_mongo_aggregate = None
    has_order_by = False
    order_mongo = None
    order_mongo_aggregate = None
    has_limit = False
    limit_mongo = None
    limit_mongo_aggregate = None

    aggregate = False

    for token in tokens:
        if token.is_whitespace: continue
        if state == "start" and (isinstance(token, sqlparse.sql.Identifier) or isinstance(token, sqlparse.sql.IdentifierList)) or token.ttype==Token.Wildcard:
            # 此时如果有多列如select a,b,c ，则token是IdentifierList 否则(select a)就是Identifier
            all_identifier = []
            if isinstance(token, sqlparse.sql.Identifier) or token.ttype==Token.Wildcard:
                all_identifier.append(token)
                # print(token)
            elif isinstance(token, sqlparse.sql.IdentifierList):
                for Identifier in token:
                    if type(Identifier) == sqlparse.sql.Token and Identifier.value == ',': continue
                    all_identifier.append(Identifier)
            for identifier in all_identifier:
                if identifier.is_whitespace: continue
                # print(identifier)
                # print(identifier.ttype)
                if identifier.ttype!=Token.Wildcard and identifier.has_alias():
                    aggregate = True
                    columns.append({"name":identifier.get_real_name(),"alias":identifier.get_alias()})
                else:
                    if identifier.ttype==Token.Wildcard:
                        columns.append({"name": identifier.value, "alias": None})
                    else:
                        columns.append({"name": identifier.get_real_name(), "alias": None})
            # print(columns)
            state = "column"
        if state == "column" and isinstance(token,sqlparse.sql.Token) and token.ttype == Token.Keyword and token.value.upper() == "FROM":
            state = "from"
        if state == "from" and (isinstance(token, sqlparse.sql.Identifier) or isinstance(token,
                                                                                         sqlparse.sql.IdentifierList)):  # or isinstance(token,sqlparse.sql.Parenthesis)):
            # 有可能是单张表、多张表、嵌套语句等
            all_identifier = []
            if isinstance(token, sqlparse.sql.Identifier):
                all_identifier.append(token)
                # print(token)
            elif isinstance(token, sqlparse.sql.IdentifierList):
                for Identifier in token:
                    if type(Identifier) == sqlparse.sql.Token and Identifier.value == ',': continue
                    all_identifier.append(Identifier)
            tables = []
            # print(all_identifier)
            for identifier in all_identifier:
                tables.append(identifier.get_real_name())
            # print(tables)

            for_order=0
            # print(tokens)
            for token in tokens:
                if isinstance(token,sqlparse.sql.Where): has_where = True
                if token.ttype==Token.Keyword and token.value.upper()=="ORDER" and tokens[for_order+2].value.upper()=="BY": has_order_by = True
                if token.ttype==Token.Keyword and token.value.upper()=="LIMIT":has_limit = True
                for_order+=1
            # print(has_where)
            # print(has_order_by)
            # print(tokens)
            if has_where:
                state="where"
            elif has_order_by:
                state="order"
            elif has_limit:
                state = "limit"
            else:
                state = "finish"
            # print(state)
        if  "where" == state and isinstance(token,sqlparse.sql.Where): #需要处理 只有一个比较 a=1 ，有多个并列比较 a=1 and b=2 ，有括号的比较 (a=1 or b=2) and c=1
            # node = {"left":None,"op":None,"right":None}

            # for where_token in token:
            #     if isinstance(where_token ,sqlparse.sql.Parenthesis) or isinstance(where_token,sqlparse.sql.Comparison) or ( where_token.ttype==Token.Keyword and (where_token.value.upper()=="AND" or where_token.value.upper()=="OR")):
            #         where_token_list.append(where_token)
            #         if isinstance(where_token ,sqlparse.sql.Parenthesis):
            #             for i in where_token:
            #                 print(i)
            #                 print(i.ttype)
            #                 print(type(i))

            where_token_list = []
            for where_token in token:
                # print(where_token)
                if isinstance(where_token, sqlparse.sql.Parenthesis) or isinstance(where_token,sqlparse.sql.Comparison) or (where_token.ttype == Token.Keyword and (where_token.value.upper() == "AND" or where_token.value.upper() == "OR")):
                    where_token_list.append(where_token)
            # print(where_token_list)
            # print(token)
            # print(token.ttype)
            # print(type(token))
            # for t in token:
            #     print(t)
            #     print(t.ttype)
            #     print(type(t))
            where_mongo = handle_where(where_token_list)
            where_mongo_aggregate = '''{$match:%s}'''%where_mongo
            # state.remove("where")
            # print(state)
            if has_order_by:
                state = "order"
            elif has_limit:
                state = "limit"
            else:
                state = "finish"
        if "order" == state and (isinstance(token,sqlparse.sql.Identifier) or isinstance(token,sqlparse.sql.IdentifierList)):
            order_list = []
            # print (token)
            # print (token.ttype)
            # print (type(token))
            if isinstance(token,sqlparse.sql.Identifier):
                column = None
                order_type = "ASC"
                for item in token:
                    # print(item)
                    # print(item.ttype)
                    # print(type(item))
                    if isinstance(item,sqlparse.sql.Identifier) or item.ttype == Token.Name:column = item.value
                    if item.ttype==Token.Keyword.Order:order_type=item.value
                order_list.append({"column":column,"order_type":order_type})
                # print(order_list)
            elif isinstance(token,sqlparse.sql.IdentifierList):
                for sub_token in token:
                #     print(sub_token)
                #     print(sub_token.ttype)
                #     print(type(sub_token))
                    if isinstance(sub_token, sqlparse.sql.Identifier):
                        column = None
                        order_type = "ASC"
                        for item in sub_token:
                            # print(item)
                            # print(item.ttype)
                            # print(type(item))
                            if isinstance(item, sqlparse.sql.Identifier) or item.ttype == Token.Name:# 没有跟着asc、desc时，其类型为token.name 而不是identifier
                                column = item.value
                            # print(column)
                            if item.ttype == Token.Keyword.Order: order_type = item.value
                        order_list.append({"column": column, "order_type": order_type})
            # for t in token:
            #     print(t)
            #     print(t.ttype)
            #     print(type(t))
            # print("---------")
            # print(order_list)
            # print("---------")
            order_mongo=""
            i=1
            for item in order_list:
                if i!=1: order_mongo+=","
                if item["order_type"].upper() == "ASC":
                    order_mongo+='''"%s":%d'''%(item["column"],1)
                else:
                    order_mongo+='''"%s":%d'''%(item["column"],-1)
                i+=1
            order_mongo_aggregate = '''{$sort:{'''+order_mongo+'''}}'''
            order_mongo = '''.sort({'''+order_mongo+'''})'''
            # print(order_mongo)
            # print(order_mongo_aggregate)
            if has_limit:
                state = "limit"
            else:
                state = "finish"
        if state == "limit" and token.ttype==Token.Literal.Number.Integer:
            limit_mongo = ".limit(%s)"%token.value
            limit_mongo_aggregate = "{$limit:%s}"%token.value
            state = "finish"
        if state == "finish":
            if aggregate == False:
                print(columns)
                if len(columns) == 1 and columns[0]["name"] == "*" and len(tables) == 1:
                    if where_mongo is None:
                        mongo = '''db.%s.find()''' % tables[0]
                    else:
                        mongo = '''db.%s.find(%s)''' % (tables[0],where_mongo)
                elif len(tables) == 1:
                    if where_mongo is None:
                        mongo = '''db.%s.find({},{ ''' % tables[0]
                    else:
                        mongo = '''db.%s.find(%s,{ ''' % (tables[0],where_mongo)
                    i = 1
                    for column in columns:
                        if i != 1: mongo += ","
                        mongo += '''%s:1''' % column["name"]
                        i += 1
                    mongo += '''})'''
                if has_order_by:
                    mongo += order_mongo
                if has_limit:
                    mongo += limit_mongo

                return(mongo)
            else:
                if len(tables)==1:
                    mongo = '''db.%s.aggregate(['''%tables[0]
                    mongo += '''{$project:{'''
                    i = 1
                    for column in columns:
                        if i != 1: mongo += ","
                        if column["alias"]!=None:
                            mongo+= '''"%s":"%s"'''%(column["alias"],column["name"])
                        else :
                            mongo+='''%s:1'''%(column["name"])
                        i+=1
                    mongo += '''}}'''# end project
                    if where_mongo_aggregate is not None:
                        mongo += ''',%s'''%where_mongo_aggregate
                    if order_mongo_aggregate is not None:
                        mongo += ''',%s'''%order_mongo_aggregate
                    if limit_mongo_aggregate is not None:
                        mongo += ''',%s''' % limit_mongo_aggregate

                    mongo += '''])'''
                return mongo


def dml_update(tokens):
    """ start -> table -> set -> mongo    example:UPDATE Person SET FirstName = 'Fred', City = 'Nanjing' WHERE LastName = 'Wilson'
        """
    state = "start"
    mongo = ""

    collection = None # table
    set = []
    has_where = False
    where_mongo = None
    for token in tokens:
        if token.is_whitespace: continue
        if state=="start" and isinstance(token, sqlparse.sql.Identifier) :
            collection = token.get_real_name()
            state = "table"
        if state == "table" and token.ttype == Token.Keyword and token.value.upper() == "SET":
            state = "set"
        if state == "set" and  (isinstance(token, sqlparse.sql.Comparison) or isinstance(token, sqlparse.sql.IdentifierList)):
            compare = []
            if isinstance(token, sqlparse.sql.IdentifierList):
                for t in token:
                    if isinstance(t, sqlparse.sql.Comparison):
                        compare.append(t)
            elif isinstance(token, sqlparse.sql.Comparison):
                compare.append(token)
            for com in compare:
                set.append({'column':com.left.value,'value':com.right.value.strip("'")})
            # print(set)
            for token in tokens:
                if isinstance(token,sqlparse.sql.Where): has_where = True
            if has_where:
                state = "where"
            else:
                state = "finish"
        if  "where" == state and isinstance(token,sqlparse.sql.Where): #需要处理 只有一个比较 a=1 ，有多个并列比较 a=1 and b=2 ，有括号的比较 (a=1 or b=2) and c=1
            where_token_list = []
            for where_token in token:
                if isinstance(where_token, sqlparse.sql.Parenthesis) or isinstance(where_token,sqlparse.sql.Comparison) or (where_token.ttype == Token.Keyword and (where_token.value.upper() == "AND" or where_token.value.upper() == "OR")):
                    where_token_list.append(where_token)
            where_mongo = handle_where(where_token_list)
            state = "finish"
        if state == "finish":
            if has_where:
                mongo = '''db.%s.updateMany(%s,{$set:{''' % (collection,where_mongo)
            else:
                mongo = '''db.%s.updateMany({},{$set:{'''%collection
            i = 1
            for s in set:
                if i != 1: mongo += ","
                mongo += '''"%s":"%s"'''%(s['column'],s['value'])
                i+=1
            mongo += '''}})'''
            return mongo

def dml_delete(tokens):
    """ start -> from -> where -> mongo    example:DELETE FROM Person WHERE LastName = 'Wilson' WHERE LastName = 'Wilson'
        """
    state = "start"
    mongo = ""

    collection = None # table
    has_where = False
    where_mongo = None
    for token in tokens:
        if token.is_whitespace: continue
        if state == "start" and token.ttype == Token.Keyword and token.value.upper()=="FROM":
            state = "from"
        if state == "from" and isinstance(token,sqlparse.sql.Identifier):
            collection = token.get_real_name()
            for token in tokens:
                if isinstance(token, sqlparse.sql.Where): has_where = True
            if has_where:
                state = "where"
            else:
                state = "finish"
        if "where" == state and isinstance(token,
                                           sqlparse.sql.Where):  # 需要处理 只有一个比较 a=1 ，有多个并列比较 a=1 and b=2 ，有括号的比较 (a=1 or b=2) and c=1
            where_token_list = []
            for where_token in token:
                if isinstance(where_token, sqlparse.sql.Parenthesis) or isinstance(where_token,
                                                                                   sqlparse.sql.Comparison) or (
                        where_token.ttype == Token.Keyword and (
                        where_token.value.upper() == "AND" or where_token.value.upper() == "OR")):
                    where_token_list.append(where_token)
            where_mongo = handle_where(where_token_list)
            state = "finish"
        if state == "finish":
            if has_where:
                mongo = "db.%s.deleteMany(%s)" % (collection,where_mongo)
            else:
                mongo = "db.%s.deleteMany({})"%collection
            return mongo

def sql_to_mongo(sql):
    res = sqlparse.parse(sql)
    tokens = res[0].tokens

    for token in tokens:
        if token.is_whitespace: continue
        if token.ttype == Token.Keyword.DML or token.ttype == Token.Keyword.DDL:
            # ------------------- DDL -------------------
            if token.value.upper() == "CREATE":
                mongo = ddl_create(tokens)
                # print(mongo)
            if token.value.upper() == "DROP":  # TODO
                mongo = ddl_drop(tokens)
                # print(mongo)
            # ------------------- DML -------------------
            if token.value.upper() == "INSERT":
                mongo = dml_insert(tokens)
                # print(mongo)
            if token.value.upper() == "SELECT":
                mongo = dml_select(tokens)
                # print(mongo)
            if token.value.upper() == "UPDATE":
                mongo = dml_update(tokens)
                # print(mongo)
            if token.value.upper() == "DELETE":
                mongo = dml_delete(tokens)
                # print(mongo)
            break
    return str(mongo)



if __name__=="__main__":
    mongo = sql_to_mongo('''select a from student''')
    print(mongo)
    # ------------------- DDL -------------------
    # res = sqlparse.parse(''''create database abc''')
    # res = sqlparse.parse('''CREATE INDEX PersonIndex ON Person (LastName DESC, FirstName)''')
    # res = sqlparse.parse('''CREATE TABLE Persons(Id_P int,LastName varchar(255),FirstName varchar(255),Address varchar(255),City varchar(255))''')
    # res = sqlparse.parse('''DROP DATABASE db1,db2''')
    # res = sqlparse.parse('''DROP TABLE Person1,Person2''')
    # res = sqlparse.parse('''DROP INDEX PersonIndex''')

    # ------------------- DML -------------------
    # res = sqlparse.parse('''select id as kd,cd from student where a <= 1 order by a,b limit 2''')
    # res = sqlparse.parse('''select id,cd from student where a <= 1 and c like "%abc%" order by id asc limit 5''')
    # res = sqlparse.parse('''UPDATE Person SET FirstName = 'Fred', City = 'Nanjing' WHERE LastName = 'Wilson' ''')
    # res = sqlparse.parse('''DELETE FROM Person WHERE LastName = 'Wilson' ''')
    # res = sqlparse.parse(''' INSERT INTO Persons (LastName, Address) VALUES ('Wilson', 'Champs-Elysees') ''')


    # tokens = res[0].tokens
    #
    # for token in tokens:
    #     if token.is_whitespace: continue
    #     if token.ttype == Token.Keyword.DML or token.ttype == Token.Keyword.DDL:
    #         # ------------------- DDL -------------------
    #         if token.value.upper()=="CREATE":
    #             mongo = ddl_create(tokens)
    #             print(mongo)
    #         if token.value.upper()=="DROP": # TODO
    #             mongo = ddl_drop(tokens)
    #             print(mongo)
    #         # ------------------- DML -------------------
    #         if token.value.upper()=="INSERT":
    #             mongo = dml_insert(tokens)
    #             print(mongo)
    #         if token.value.upper()=="SELECT":
    #             mongo = dml_select(tokens)
    #             print(mongo)
    #         if token.value.upper()=="UPDATE":
    #             mongo = dml_update(tokens)
    #             print(mongo)
    #         if token.value.upper()=="DELETE":
    #             mongo = dml_delete(tokens)
    #             print(mongo)
    #         break
    #


        #============================ DDL-create ==================================================
        # if sentence_type == "create":
        # ============================ DDL-drop ==================================================
        # if sentence_type == "drop":

        # ============================ DML-select ==================================================
        # if sentence_type == "select":


