import inspect
import pickle

from .connections import SimpleConnectionFactory


__version__ = "0.1.0"


class YoTon(object):
    """A cache util which can simplify cache with a decorator.
    Basic Usage:

        cache_servers = {
            'default': {
                'host': 'localhost'
            }
        }
        yoton = YoTon(cache_server)
        
        @yoton.cache("test_cache_key:{arg1}_{arg2}_{arg3}", expire_seconds=600)
        def dummy_func(arg1, arg2=3, arg3=None):
            return arg1 + arg2 + (arg3 or 0)

    The default implementation is using Redis as the cache layer, but
    you can implement your own ``.connections.ConnectionFactory`` to extend
    it to other cache databases.

    Notice: cache decorator currently only support function and instance
    method. staticmethod and classmethod are not supported now. You could
    just use function in those circumstances.
    """

    def __init__(self, cache_servers,
                 connection_factory_cls=SimpleConnectionFactory,
                 serializer=pickle):
        """Initializer

        :param cache_servers: a dict of cache server config, the key of this
            dict is treated as an alias which can be used for database select in
            ``.cache`` decorator, its value a key-value config which needed by
            the underlay connection, by default it is redis so the possible
            config is what is defined in the construct of ``redis.Redis``.
            As for example:

                {
                    'default': {
                        'host': 'localhost',
                        'port': '6379'
                    },
                    ...
                }

            There is a special key ``default`` in it, which will be used if
            there is no config for specific database
        :param connection_factory_cls: a class which implemented
            ``.connection.ConnectionFactory`` it will provide the connection
            instance to access the underlay cache server
        :param serializer: serializer is a mechanism for object serialization,
            by default it is cPickle, you could use other serializer as long
            as it has ``dumps`` and ``loads`` for serialize and deserialize
        """
        self.connection_factory = connection_factory_cls(cache_servers)
        self.serializer = serializer

    def cache(self, key_pattern, expire_seconds, key_formatter=None,
              database=None):
        """Cache decorator which can be applied to function and instance
        method. Target function will be wrapped as a ``CacheWrapper`` object
        which provides an automatic way to set cache after function calls.

        :param key_pattern: the pattern for the cache key, it use the syntax
            of string format, and the values it use to format this pattern
            come from the function call's parameters.
        :param expire_seconds: expire time in seconds
        :param key_formatter: custom string formatter which will be used
            to format the key
        :param database: database name which this function will use, the name
            is defined in the cache_servers of ``YoTon``
        :return: an instance of ``CacheWrapper``
        """
        def inner(func):
            return CacheWrapper(
                self,
                func,
                key_pattern=key_pattern,
                expire_seconds=expire_seconds,
                key_formatter=key_formatter,
                database=database
            )
        return inner


class CacheWrapper(object):
    """A wrapper to a function or instance method which provides a set
    of utils to set cache, refresh cache, call without cache and
    delete cache.
    """

    def __init__(self, yoton, func, key_pattern, expire_seconds,
                 key_formatter=None, database=None):
        """Initializer

        :param yoton: a ``YoTon`` instance
        :param func: the function which will be wrapped
        :param key_pattern: the key_pattern which will be used to construct
            cache key, it uses the same syntax as string format
        :param expire_seconds: expire time in seconds
        :param key_formatter: custom string formatter which will be used
            to format the key
        :param database: database name which this function will use, the name
            is defined in the cache_servers of ``YoTon``
        """
        self.yoton = yoton
        self.func = func
        self.key_pattern = key_pattern
        self.key_formatter = key_formatter
        self.expire_seconds = expire_seconds
        self.database = database
        self.out_caller = None

    def __get__(self, instance, instance_type):
        # used to get he out caller of instance method, the caller
        # will later be used as "self" to call instance method
        self.out_caller = instance or instance_type
        return self

    def __call__(self, *args, **kwargs):
        cache_key = self._get_cache_key(*args, **kwargs)
        connection = self.yoton.connection_factory.get_connection(
            cache_key, self.database)
        data = connection.get(cache_key)
        if data is not None:
            return_val = self.yoton.serializer.loads(data)
        else:
            return_val = self._execute_function(*args, **kwargs)
            serialized_data = self.yoton.serializer.dumps(return_val)
            connection.setex(cache_key, time=self.expire_seconds,
                             value=serialized_data)
        return return_val

    def call(self, *args, **kwargs):
        """Direct call to function without touch cache, it won't fill
        cache with data either"""
        return self._execute_function(*args, **kwargs)

    def refresh_cache(self, *args, **kwargs):
        """Refresh cache data, it data is exist in cache and this method
        could be used to renew it. And please notice that if the later
        call's return value is None the prior data in cache will also be
        removed."""
        return_val = self._execute_function(*args, **kwargs)
        cache_key = self._get_cache_key(*args, **kwargs)
        connection = self.yoton.connection_factory.get_connection(
            cache_key, self.database)
        if return_val is not None:
            serialized_data = self.yoton.serializer.dumps(return_val)
            connection.setex(cache_key, time=self.expire_seconds,
                             value=serialized_data)
        else:
            connection.delete(cache_key)
        return return_val

    def delete_cache(self, *args, **kwargs):
        """Delete data in cache"""
        cache_key = self._get_cache_key(*args, **kwargs)
        connection = self.yoton.connection_factory.get_connection(
            cache_key, self.database)
        connection.delete(cache_key)

    def _execute_function(self, *args, **kwargs):
        if self.out_caller:
            return self.func(self.out_caller, *args, **kwargs)
        else:
            return self.func(*args, **kwargs)

    def _get_cache_key(self, *args, **kwargs):
        if not (inspect.ismethod(self.func) or inspect.isfunction(self.func)):
            raise TypeError(
                "staticmethod and classmethod are not supported now,"
                "please check your func {}".format(self.func))
        if self.out_caller:
            parameters = inspect.getcallargs(
                self.func, self.out_caller, *args, **kwargs)
        else:
            parameters = inspect.getcallargs(self.func, *args, **kwargs)

        if self.key_formatter:
            return self.key_formatter.format(self.key_pattern, **parameters)
        else:
            return self.key_pattern.format(**parameters)
