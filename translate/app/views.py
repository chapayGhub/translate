 # -*- coding: utf-8 -*-

from translate.app import app, log
from translate.app.ratelimit import get_view_rate_limit, ratelimit, RateLimit
from translate.exceptions import APIException, TranslationException
from translate import __version__

import translate.app
import translate.utils

import flask
from flask import render_template, request

import json

manager = None


@app.after_request
def inject_x_rate_headers(response):
    """Add ratelimit headers to response if the requested URL is an API
    endpoint that requires rate-limiting
    """

    limit = get_view_rate_limit()
    if limit and limit.send_x_headers:
        h = response.headers
        h.add('X-RateLimit-Remaining', str(limit.remaining))
        h.add('X-RateLimit-Limit', str(limit.limit))
        h.add('X-RateLimit-Duration', str(RateLimit.per))
    return response


@app.errorhandler(APIException)
@translate.utils.jsonp
def bad_request(error):

    return error.jsonify()


@app.route('/')
def index():
    return render_template('index.html', version=__version__)


@app.route('/api/')
def api():
    pairs = set()

    for backend in manager.backends:
        for pair in backend.language_pairs:
            pairs.add(pair)

    return render_template('api.html',
                           version=translate.__version__,
                           backends=manager.backends,
                           pairs=list(pairs))


@app.route('/api/v1/translators')
@ratelimit()
@translate.utils.jsonp
def list_translators():
    return flask.jsonify(
        backends=[{
            'name': b.name,
            'description': b.description,
            'url': b.url,
            'preference': b.preference,
            'pairs': b.language_pairs
        } for b in manager.backends])


@app.route('/api/v1/pairs')
@ratelimit()
@translate.utils.jsonp
def list_pairs():

    pairs = set()

    for backend in manager.backends:
        for pair in backend.language_pairs:
            pairs.add(pair)

    return flask.jsonify(pairs=list(pairs))


@app.route('/api/v1/translate')
@ratelimit()
@translate.utils.jsonp
def translate_text():

    text = request.args.get('text', None)
    if not text:
        raise APIException.translate(msg='No translation text given')

    source_lang = request.args.get('from', None)
    if not source_lang:
        raise APIException.translate(msg='No source language given')

    dest_lang = request.args.get('to', None)
    if not dest_lang:
        raise APIException.translate(msg='No destination language given')

    # Try each translator sequentially (sorted by preference) until one works
    backends = manager.find_all(source_lang, dest_lang)
    for backend in backends:
        try:
            trans = backend.translate(text, source_lang, dest_lang)
            return flask.Response(json.dumps({
                'from': source_lang,
                'to': dest_lang,
                'result': trans
            }), mimetype='application/json')

        except TranslationException as exc:
            log.warning('{0} failed to translate text: {1}'
                        .format(backend.name, exc))

    raise APIException.translator(from_lang=source_lang, to_lang=dest_lang,
                                  text=text, tried=[b.name for b in backends])
