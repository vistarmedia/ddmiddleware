from hashlib import sha224
from socket import gethostname
from sys import exc_info
from traceback import format_tb

from dogapi.http import DogHttpApi


class DatadogMiddleware:
  def __init__(self, app, **kwargs):
    self.app = app
    if 'api_key' not in kwargs or 'application_key' not in kwargs:
      raise Exception("Datadog Middleware needs to be passed a dict with api "+
          "key and application key")

    self.dog_api = DogHttpApi(kwargs['api_key'], kwargs['application_key'])

  def __call__(self, environ, start_response):
    app_iter = None
    # just call the application and send the output back unchanged but catch
    # exceptions
    try:
      app_iter = self.app(environ, start_response)
      for item in app_iter:
        yield item

    # if an exception occours we get the exception information and prepare a
    # traceback we can render
    except:
      e_type, e_value, tb = exc_info()
      traceback = ['Traceback (most recent call last):'] + format_tb(tb)
      traceback.append('%s: %s' % (e_type.__name__, e_value))

      title = "Internal Server Error (%s: %s)" % (e_type.__name__, e_value)
      self.dog_api.event(
        title=title,
        aggregation_key=sha224(title).hexdigest(),
        text='\n'.join(traceback),
        host=gethostname()
      )
      start_response('500 INTERNAL SERVER ERROR', [
                      ('Content-Type', 'text/plain')])
      raise

    # wsgi applications might have a close function. If it exists it *must* be
    # called.
    if hasattr(app_iter, 'close'):
      app_iter.close()
