import os
from flask import Flask

def create_app(test_config=None):
    app = Flask(__name__,instance_relative_config=True)
    if test_config is None:
        app.config.from_pyfile('config.py',silent=True)
    else:
        app.config.from_mapping(test_config)

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    
    from . import base
    app.register_blueprint(base.bp)

    UPLOAD_FOLDER = os.path.join(app.instance_path,'uploads')
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    try:
        os.makedirs(app.config['UPLOAD_FOLDER'])
    except OSError:
        pass

    app.debug = True
    return app

