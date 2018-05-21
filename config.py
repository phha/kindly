import os
basedir = os.path.abspath(os.path.dirname(__file__))

SECRET_KEY = os.environ.get(
    'SECRET_KEY') or 'c62299aaa3357011dc6ff9fb73c63f0c'
SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///' + os.path.join(basedir, 'kindly.db')
SQLALCHEMY_TRACK_MODIFICATIONS = False

