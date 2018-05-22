from contextlib import contextmanager
from collections import OrderedDict
from datetime import datetime, timedelta
import functools
import feedparser
from flask import Flask, render_template, url_for, flash, redirect
from flask_bootstrap import Bootstrap
from flask_bootstrap.nav import BootstrapRenderer
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_nav import Nav, register_renderer
from flask_nav.elements import View, Subgroup, Navbar
from flask_login import LoginManager
import config

app = Flask(__name__)
app.config.from_object('config')
try:
    app.config.from_envvar('KINDLY_SETTINGS')
except RuntimeError:
    app.logger.warn('Could not load configuration file. Using defaults.')
db = SQLAlchemy(app)
migrate = Migrate(app, db)
bootstrap = Bootstrap(app)
nav = Nav(app)
login = LoginManager(app)

import models
import forms
from models import User, Feed

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Feed': Feed, 'models': models}


class FixedNavBarRenderer(BootstrapRenderer):
    def visit_Navbar(self, node):
        nav_tag = super().visit_Navbar(node)
        nav_tag['class'] += 'navbar navbar-default navbar-fixed-top'
        return nav_tag

register_renderer(app, 'fixed', FixedNavBarRenderer)

@login.user_loader
def load_user(id):
    return User.query.get(int(id))

@nav.navigation()
def top_navbar():
    feed_views = [View(t, 'feed', feed_name=t) for t in load_feeds().keys()]
    return Navbar(
        'Kindly',
        View('Home', 'index'),
        Subgroup(
            'Feeds',
            *feed_views)
    )

def timed_cache(cache_time):
    def decorator(f):
        class cache_wrapper:
            def __init__(self, f):
                self.__cache_time = cache_time
                self.__last_updated = None
                self.__wrapped_f = f
                self.__cached_v = None
                functools.update_wrapper(self, f)

            def __call__(self, *args, **kwargs):
                now = datetime.now()
                if not self.__last_updated or now - self.__last_updated > self.__cache_time:
                    self.__last_updated = now
                    self.__cached_v = self.__wrapped_f(*args, **kwargs)
                return self.__cached_v

        return cache_wrapper(f)
    return decorator

urls = list()
with app.open_instance_resource('feeds', 'r') as f:
    urls = f.readlines()

@timed_cache(timedelta(seconds=10))
def load_feeds():
    feeds = OrderedDict()
    for url in urls:
        try:
            app.logger.info("Parsing feed {0}".format(url))
            d = feedparser.parse(url)
            feeds[d.feed.title] = d
        except Exception as e:
            app.logger.warn("Exception while trying to parse {0}".format(url))
            app.logger.warn(e)
    return feeds


@app.route('/')
@app.route('/index')
def index():
    return render_template('feed_list.html', feeds=list(load_feeds().values()))

@app.route('/feed/<feed_name>')
def feed(feed_name):
    entries = load_feeds()[feed_name].entries
    return render_template('feed.html', entries=load_feeds()[feed_name].entries, feed_name=feed_name)

@app.route('/login')
def login():
    form = forms.LoginForm()
    return render_template('form.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = forms.RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Registration successfull. Please log in.')
        return redirect(url_for('login'))
    return render_template('form.html', form=form)

