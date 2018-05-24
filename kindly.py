from collections import OrderedDict
from datetime import datetime, timedelta
import requests
from justext import justext, get_stoplists, get_stoplist
import feedparser
from flask import Flask, render_template, url_for, flash, redirect, request
from flask_caching import Cache
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, current_user, login_user, login_required, logout_user
from werkzeug.urls import url_parse
from paginate import Pagination
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
cache = Cache(
    app,
    config={'CACHE_TYPE': config.CACHE_TYPE,
            'CACHE_DEFAULT_TIMEOUT': config.CACHE_DEFAULT_TIMEOUT})


@cache.memoize()
def parse_feed(url):
    return feedparser.parse(url)


stopwords = set()
for language in get_stoplists():
    stopwords.update(get_stoplist(language))


import models
import forms
from models import User, Feed


@app.shell_context_processor
def make_shell_context():
    return {
        'db': db,
        'User': User,
        'Feed': Feed,
        'models': models,
        'Pagination': Pagination
    }


@login.user_loader
def load_user(id):
    return User.query.get(int(id))


@app.route('/')
@app.route('/index')
@app.route('/feeds')
@login_required
def index():
    return render_template('feed_list.html', feeds=current_user.feeds.all())


@app.route('/feed/<int:id>')
@login_required
def feed(id):
    page = request.args.get('page', 1, type=int)
    feed = Feed.query.get(id)
    if feed.user.id != current_user.id:
        flash('This feed does not belong to you.')
        return redirect('index')
    parsed_feed = feed.parse()
    pagination = Pagination(
        parsed_feed.entries, page=page, per_page=config.ENTRIES_PER_PAGE)
    return render_template(
        'feed.html', title=parsed_feed.feed.title, entries=pagination)


@app.route('/read/<path:url>')
@login_required
def read(url):
    title = request.args.get('article_title', None, type=str)
    app.logger.info("Article title: {0}".format(title))
    response = requests.get(url)
    paragraphs = justext(response.content, stopwords)
    return render_template(
        'read.html', paragraphs=paragraphs,
        article_title=title, original_article=url)


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
            login_user(user, remember=True)
            next_page = request.args.get('next')
            if not next_page or url_parse(next_page).netloc != '':
                next_page = url_for('index')
            flash("Logged in as {0}".format(user.username))
            return redirect(next_page)
    return render_template('login.html', form=form)


@app.route('/logout')
def logout():
    logout_user()
    flash('You are logged out.')
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
