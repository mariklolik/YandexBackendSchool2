from dbremote import db_session
from flask import Flask
import os
import api_new

app = Flask(__name__)
app.config["SECRET_KEY"] = "sk"
UPLOAD_FOLDER = '/data'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def main():
    db_session.global_init("db/data.sqlite")
    port = int(os.environ.get("PORT", 80))
    app.register_blueprint(api_new.blueprint)
    app.run(port=port, host='0.0.0.0', debug=True)
    return 0


