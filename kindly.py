from collections import OrderedDict
from datetime import datetime, timedelta
import functools
import feedparser
from flask import Flask, render_template, url_for
from flask_bootstrap import Bootstrap

app = Flask(__name__)
bootstrap = Bootstrap(app)


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
