"""Helpers for WebOb requests and responses."""

import webob
from collections import MutableMapping
from lazy import lazy
from itertools import chain, repeat, izip
from webob.multidict import MultiDict, NestedMultiDict, NoVars


def webob_to_django_response(webob_response):
    """Returns a django response to the `webob_response`"""
    from django.http import HttpResponse
    django_response = HttpResponse(
        webob_response.app_iter,
        content_type=webob_response.content_type
    )
    for name, value in webob_response.headerlist:
        django_response[name] = value
    return django_response


class HeaderDict(MutableMapping):
    """
    Provide a dictionary view of the HTTP headers in a
    Django request.META dictionary that translates the
    keys into actually HTTP header names
    """
    UNPREFIXED_HEADERS = ('CONTENT_TYPE', 'CONTENT_LENGTH')

    def __init__(self, meta):
        self._meta = meta

    def _meta_name(self, name):
        """
        Translate HTTP header names to the format used by Django request objects.

        See https://docs.djangoproject.com/en/1.4/ref/request-response/#django.http.HttpRequest.META
        """
        name = name.upper().replace('-', '_')
        if name not in self.UNPREFIXED_HEADERS:
            name = 'HTTP_' + name
        return name

    def _un_meta_name(self, name):
        """
        Reverse of _meta_name
        """
        if name.startswith('HTTP_'):
            name = name[5:]
        return name.replace('_', '-').title()

    def __getitem__(self, name):
        return self._meta[self._meta_name(name)]

    def __setitem__(self, name, value):
        self._meta[self._meta_name(name)] = value

    def __delitem__(self, name):
        del self._meta[self._meta_name(name)]

    def __iter__(self):
        for key in self._meta:
            if key in self.UNPREFIXED_HEADERS or key.startswith('HTTP_'):
                yield self._un_meta_name(key)

    def __len__(self):
        return len(list(self))


def querydict_to_multidict(query_dict, wrap=None):
    """
    Returns a new `webob.MultiDict` from a `django.http.QueryDict`.

    If `wrap` is provided, it's used to wrap the values.

    """
    wrap = wrap or (lambda val: val)
    return MultiDict(chain.from_iterable(
        izip(repeat(key), (wrap(v) for v in vals))
        for key, vals in query_dict.iterlists()
    ))


class DjangoUploadedFile(object):
    """
    Looks like a FieldStorage, but wraps a Django UploadedFile.
    """
    def __init__(self, uploaded):
        self.uploaded = uploaded

    def __getattr__(self, name):
        return getattr(self.uploaded, name)

    @property
    def name(self):
        """The name of the input element used to upload the file."""
        return self.uploaded.field_name

    @property
    def filename(self):
        """The name of the uploaded file."""
        return self.uploaded.name


class DjangoWebobRequest(webob.Request):
    """
    An implementation of the webob request api, backed
    by a django request
    """
    def __init__(self, request):
        self._request = request
        super(DjangoWebobRequest, self).__init__(self.environ)

    @lazy
    def environ(self):
        environ = dict(self._request.META)

        environ['PATH_INFO'] = self._request.path_info

        return environ

    @property
    def GET(self):
        return querydict_to_multidict(self._request.GET)

    @property
    def POST(self):
        if self.method not in ('POST', 'PUT', 'PATCH'):
            return NoVars('Not a form request')

        return NestedMultiDict(
            querydict_to_multidict(self._request.POST),
            querydict_to_multidict(self._request.FILES, wrap=DjangoUploadedFile),
        )

    @lazy
    def body(self):
        return self._request.body

    @lazy
    def body_file(self):
        return self._request


def django_to_webob_request(django_request):
    """Returns a WebOb request to the `django_request`"""
    return DjangoWebobRequest(django_request)