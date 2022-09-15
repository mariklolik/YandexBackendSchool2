from dbremote import db_session
from flask import Flask
import api_new

app = Flask(__name__)
app.config["SECRET_KEY"] = "sk"
UPLOAD_FOLDER = '/data'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
db_session.global_init("db/data.sqlite")
app.register_blueprint(api_new.blueprint)
