import os
basedir = os.path.abspath(os.path.dirname(__file__))
get = os.environ.get

SECRET_KEY = get('SECRET_KEY') or 'c62299aaa3357011dc6ff9fb73c63f0c'
SQLALCHEMY_DATABASE_URI = get('DATABASE_URL') or 'sqlite:///' + os.path.join(basedir, 'kindly.db')
SQLALCHEMY_TRACK_MODIFICATIONS = False
CACHE_TYPE = get('CACHE_TYPE') or 'simple'
CACHE_DEFAULT_TIMEOUT = int(get('CACHE_DEFAULT_TIMEOUT') or 300)
ENTRIES_PER_PAGE = int(get('ENTRIES_PER_PAGE') or 5)
