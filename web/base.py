from flask import Blueprint,render_template,make_response,request,jsonify,current_app
import os
from werkzeug import secure_filename
import SqlMongo

bp = Blueprint('base',__name__)
@bp.route('/')
def index():
    return render_template('index.html')

@bp.route("/trans/",methods=['GET','POST'])
def solve_trans():
    req_type = request.form["type"]
    if req_type=="text" :
        res = request.form["data"]
        # write handle sql text here
        res = SqlMongo.sql_to_mongo(res)
        pass
    elif req_type=="file":
        # this is a get and print result example
        file = request.files["data"]
        filename = secure_filename(file.filename)
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'],filename)
        file.save(file_path)

        # write handle sql file here 
        # and save the mongodb result file 
        # and 

        file = open(file_path)
        text = file.read()
        sql_list = text.split(";")
        res=""
        print(sql_list)
        for i in sql_list:
            if i !="":
                res += SqlMongo.sql_to_mongo(i)+";\n"
        pass
    
    data = jsonify({"result":res,"error":"","type":req_type})
    response = make_response(data,200)
    return response