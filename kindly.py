from collections import OrderedDict
from datetime import datetime, timedelta
import functools
import feedparser
from flask import Flask, render_template, url_for, flash, redirect, request
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, current_user, login_user, login_required, logout_user
from werkzeug.urls import url_parse
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
login = LoginManager(app)
login.login_view = 'login'

import models
import forms
from models import User, Feed


@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Feed': Feed, 'models': models}


@login.user_loader
def load_user(id):
    return User.query.get(int(id))


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
@app.route('/feeds')
@login_required
def index():
    return render_template('feed_list.html', feeds=current_user.feeds.all())


@app.route('/feed/<feed_name>')
@login_required
def feed(feed_name):
    entries = load_feeds()[feed_name].entries
    return render_template('feed.html', entries=entries, feed_name=feed_name)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = forms.LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('index'))
        else:
            login_user(user)
            next_page = request.args.get('next')
            if not next_page or url_parse(next_page).netloc != '':
                next_page = url_for('index')
            flash("Logged in as {0}".format(user.username))
            return redirect(next_page)
    return render_template('login.html', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = forms.RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful. Please log in.')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)


@app.route('/manage', methods=['GET', 'POST'])
@login_required
def manage():
    form = forms.AddFeedForm()
    if form.validate_on_submit():
        feed = Feed(url=form.url.data,
                    title=form.title.data, user=current_user)
        try:
            parsed_feed = feed.parse()
            if not feed.title:
                feed.title = parsed_feed.feed.title
        except RuntimeError:
            flash(
                'Could not parse the feed. Please check if the URL is correct')
            return redirect(url_for('manage'))
        db.session.add(feed)
        db.session.commit()
        flash("Added feed '{0}'".format(feed.title))
        return redirect(url_for('manage'))
    return render_template(
        'manage.html', feeds=current_user.feeds.all(), form=form)


@app.route('/delete/<int:feed_id>')
@login_required
def delete(feed_id):
    feed = Feed.query.get(feed_id)
    db.session.delete(feed)
    db.session.commit()
    flash("Deleted feed '{0}'".format(feed.title))
    return redirect(url_for('manage'))
