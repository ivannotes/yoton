YoTon
=========

.. image:: https://travis-ci.org/ivannotes/yoton.svg?branch=master
    :target: https://travis-ci.org/ivannotes/yoton

YoTon is an util for cache, it simplifier cache with a decorator.

Configuration
----------------------

.. code-block:: python

    redis_server_config = {
        "default": {
            "host": "localhost",
            "port": 6379,
            "db": 1
        },
        "server_a": {
            "host": "localhost",
            "port": 6378,
            "db": 2,
        }
    }
    yoton = YoTon(redis_server_config)
    
Apply To Function
----------------------

.. code-block:: python

    @yoton.cache(key_pattern="dummy_cache_key", expire_seconds=60)
    def dummy_func():
        return "hello"

    >> dummy_func()  # call the function
    "hello" set in the cache

Key Pattern
----------------------

The cache key is using python's string format syntax, you can find it here

.. code-block:: python

    @youton.cache(key_pattern="dummy:{a}_{b}_{c}", expire_seconds=60)
    def dummy_func_with_params(a, b, c=3):
        return a + b + c

Complex object in parameters

.. code-block:: python

    @youton.cache(key_pattern="dummy:{a.id}_{b.name}", expire_seconds=60)
    def dummy_func_with_params(a, b):
        return a + b

Select Database
----------------------

.. code-block:: python

    @yoton.cache(key_pattern="dummy_cache_key", database="test", expire_seconds=60)
    def dummy_func_database():
        return "hello"

Customized Formatter
---------------------

.. code-block:: python

    @yoton.cache(key_pattern="dummy_cache_key", key_formatter=CustomizedFormatter(), expire_seconds=60)
    def dummy_func_keyforamtter():
        pass

Apply Cache To Instance Method
-------------------------------

.. code-block:: python

    class DummyClass(object):

        @yoton.cache(key_pattern="instance_method")
        def instance_method(self):
            return "hello"

Misc
---------
    
.. code-block:: python

    # call the function directly without touch cache
    dummy_func_with_params.call(a=1, b=2, c=3)

    # refresh cache data
    dummy_func_with_params.refresh_cache(a=1, b=2, c=3)

    # remove data in cache
    dummy_func_with_params.delete_cache(a=1, b=2, c=3)
