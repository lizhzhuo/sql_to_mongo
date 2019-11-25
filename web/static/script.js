window.onload=function(){
    select_view = document.getElementById('select_view');
    select_view.addEventListener('change',function(){change_view(select_view.value)});
    transform_but = document.getElementById('transform_btn');
    transform_but.addEventListener('click',transform);

}
function change_view(value){
    //console.log('change_view!');
    switch(value){
        case '1':
            document.getElementById('input_sql').hidden=false;
            document.getElementById('show_mongo').hidden=false;
            document.getElementById('upload_file').hidden=true;
            document.getElementById('down_file').hidden=true;
            break;
        case '2':
            document.getElementById('input_sql').hidden=true;
            document.getElementById('show_mongo').hidden=true;
            document.getElementById('upload_file').hidden=false;
            document.getElementById('down_file').hidden=false;
            break;
    }
}

function transform(){
    
    data = get_input();
    sendRequest('http://127.0.0.1:5000/trans/','POST',data,solve_response);
}

function solve_response(data){
    res = JSON.parse(data);
    if (res["error"]=="" ){
        show_result(res["result"],res["type"]);
    }else{
        show_error(res["error"]);
    }
}

function get_input(){    
    var formData = new FormData();
    if (document.getElementById('input_sql').hidden){
        input_div = document.getElementById('upload_file');
        input = input_div.children[0].files[0];
        formData.append("type","file");
    } else{
        input_div =document.getElementById('input_sql');
        input = input_div.children[0].value;
        formData.append("type","text");
    }
    formData.append("data",input);
    return formData;
}

function show_result(result,type){
    if(type=="text"){
        show_mongo_area = document.getElementById("show_mongo").children[0];
        show_mongo_area.value = result;    
    }else{
        down_a = document.getElementById("down_file").children[0];
        input_div = document.getElementById('upload_file');
        input = input_div.children[0].files[0];
        fileName = input.name;
        down_a.download = fileName;
        down_a.href = "data:text/plain," + result;
        down_a.hidden = false;
    }
    console.log(result);
}

function show_error(info){
    info_area = document.getElementById("error_area");
    info_area.value = info;
}

function sendRequest(url,method,data,func){
    ajax = new XMLHttpRequest();
    ajax.onreadystatechange=function(){
        if (ajax.readyState==4 && ajax.status==200){
            response_text=ajax.responseText;
            func(response_text)
        }
    }
    ajax.open(method,url,true);
    ajax.send(data);
}