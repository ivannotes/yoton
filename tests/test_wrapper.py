from unittest import TestCase, main
import cPickle

from mock import patch
from redis import Redis

from yoton import YoTon


def function_without_args():
    return "hello"


def function_with_args(arg1, arg2=3, arg3=None):
    return arg1 + arg2 + (arg3 or 0)


def function_with_complex_args(obj1, obj2):
    return obj1.name + obj2.name


TEST_REDIS_CONFIG = {
    "default": {
        "host": "localhost"
    },
    "test": {
        "host": "localhost",
        "db": "1"
    }
}
dummy_yoton = YoTon(TEST_REDIS_CONFIG)


def _inner_func_for_mock():
    pass


@dummy_yoton.cache("test_decorator_{arg1}_{arg2}_{arg3}", expire_seconds=60)
def function_call_with_decorator(arg1, arg2=2, arg3=None):
    return _inner_func_for_mock()


class DummyClass(object):
    name = "dummy"

    @dummy_yoton.cache("test_with_args_{arg1}_{arg2}_{arg3}", expire_seconds=60)
    def in_class_function_with_args(self, arg1, arg2=3, arg3=None):
        return self.name + str(arg1 + arg2 + (arg3 or 0))

    @dummy_yoton.cache("test_without_args", expire_seconds=60)
    def in_class_function_without_args(self):
        return "hello"


class CacheWrapperTest(TestCase):

    def setUp(self):
        self.test_yoton = YoTon(TEST_REDIS_CONFIG)
        self.redis = Redis(host='localhost')
        self.second_redis = Redis(host='localhost', db=1)

    def tearDown(self):
        self.redis.flushall()
        self.second_redis.flushall()

    def test_function_without_param(self):
        wrapped_func = self.test_yoton.cache(key_pattern="test", expire_seconds=1)(
            function_without_args
        )
        result = wrapped_func()
        self.assertEqual(result, "hello")

    def test_fuction_with_args(self):
        wrapped_func = self.test_yoton.cache(
            key_pattern="test_{arg1}_{arg2}_{arg3}",
            expire_seconds=1
        )(function_with_args)
        result = wrapped_func(1, 2, 3)
        self.assertEqual(result, 6)

    def test_get_key_of_function_without_args(self):
        wrapped_func = self.test_yoton.cache(key_pattern="test", expire_seconds=1)(
            function_without_args
        )
        key = wrapped_func._get_cache_key()
        self.assertEqual(key, "test")

    def test_get_key_of_function_with_args(self):
        wrapped_func = self.test_yoton.cache(
            key_pattern="test_{arg1}_{arg2}_{arg3}",
            expire_seconds=1
        )(function_with_args)
        key = wrapped_func._get_cache_key(1, 2, 3)
        self.assertEqual(key, "test_1_2_3")

    def test_get_key_with_default_value(self):
        wrapped_func = self.test_yoton.cache(
            key_pattern="test_{arg1}_{arg2}_{arg3}",
            expire_seconds=1
        )(function_with_args)
        key = wrapped_func._get_cache_key(1)
        self.assertEqual(key, "test_1_3_None")

    def test_get_key_of_function_with_complex_parameter(self):
        wrapped_func = self.test_yoton.cache(
            key_pattern="test_obj_param_{obj1.name}_{obj2.name}",
            expire_seconds=1
        )(function_with_complex_args)
        TestObj = type("TestObj", (object, ), {})
        obj1 = TestObj()
        obj1.name = "name1"
        obj2 = TestObj()
        obj2.name = "name2"
        key = wrapped_func._get_cache_key(obj1, obj2)
        self.assertEqual(key, "test_obj_param_name1_name2")

    def test_get_key_with_instance_method_without_parameter(self):
        key = DummyClass().in_class_function_without_args._get_cache_key()
        self.assertEqual(key, "test_without_args")

    def test_get_key_with_instance_method_with_parameters(self):
        key = DummyClass().in_class_function_with_args._get_cache_key(1)
        self.assertEqual(key, "test_with_args_1_3_None")

    def test_instance_method_call_without_parameters(self):
        result = DummyClass().in_class_function_without_args()
        self.assertEqual(result, "hello")

    def test_instance_method_call_with_parameters(self):
        result = DummyClass().in_class_function_with_args(1)
        self.assertEqual(result, "dummy4")

    @patch("tests.test_wrapper._inner_func_for_mock")
    def test_data_did_cached(self, mock_func_call):
        mock_func_call.side_effect = ["hello", "hello again"]
        return_val = function_call_with_decorator(1, 3, 5)
        self.assertEqual(return_val, "hello")
        data = self.redis.get("test_decorator_1_3_5")
        data_in_cache = cPickle.loads(data)
        self.assertEqual(data_in_cache, "hello")
        ttl = self.redis.ttl("test_decorator_1_3_5")
        self.assertTrue(0 < ttl <= 60)
        second_return_val = function_call_with_decorator(1, 3, 5)
        self.assertEqual(second_return_val, "hello")

    @patch("tests.test_wrapper._inner_func_for_mock")
    def test_data_call_without_cache(self, mock_func_call):
        mock_func_call.side_effect = ["hello", "hello again"]
        return_val = function_call_with_decorator(1, 3, 5)
        self.assertEqual(return_val, "hello")
        function_call_with_decorator(1, 3, 5)
        direct_return_val = function_call_with_decorator.call(1, 3, 5)
        self.assertEqual(direct_return_val, "hello again")

    @patch("tests.test_wrapper._inner_func_for_mock")
    def test_refresh_cache_call(self, mock_func_call):
        mock_func_call.side_effect = ["hello", "hello again"]
        return_val = function_call_with_decorator(1, 3, 5)
        self.assertEqual(return_val, "hello")
        second_return_val = function_call_with_decorator(1, 3, 5)
        self.assertEqual(second_return_val, "hello")
        direct_return_val = function_call_with_decorator.refresh_cache(1, 3, 5)
        self.assertEqual(direct_return_val, "hello again")
        data = self.redis.get("test_decorator_1_3_5")
        value = cPickle.loads(data)
        self.assertEqual(value, "hello again")
        ttl = self.redis.ttl("test_decorator_1_3_5")
        self.assertTrue(0 < ttl <= 60)

    @patch("tests.test_wrapper._inner_func_for_mock")
    def test_refresh_call_with_none_value(self, mock_func_call):
        mock_func_call.side_effect = ["hello", None]
        return_val = function_call_with_decorator(1, 3, 5)
        self.assertEqual(return_val, "hello")
        second_return_val = function_call_with_decorator(1, 3, 5)
        self.assertEqual(second_return_val, "hello")
        direct_return_val = function_call_with_decorator.refresh_cache(1, 3, 5)
        self.assertIsNone(direct_return_val)
        data = self.redis.get("test_decorator_1_3_5")
        self.assertIsNone(data)

    @patch("tests.test_wrapper._inner_func_for_mock")
    def test_delete_cache_call(self, mock_func_call):
        mock_func_call.side_effect = ["hello", None]
        return_val = function_call_with_decorator(1, 3, 5)
        self.assertEqual(return_val, "hello")
        data = self.redis.get("test_decorator_1_3_5")
        self.assertIsNotNone(data)
        function_call_with_decorator.delete_cache(1, 3, 5)
        data = self.redis.get("test_decorator_1_3_5")
        self.assertIsNone(data)

    def test_cache_call_with_selected_database(self):
        wrapped_func = self.test_yoton.cache(
            key_pattern="test_{arg1}_{arg2}_{arg3}",
            expire_seconds=60,
            database="test"
        )(function_with_args)
        result = wrapped_func(1, 2, 3)
        self.assertEqual(result, 6)
        data = self.second_redis.get("test_1_2_3")
        value = cPickle.loads(data)
        self.assertEqual(value, 6)


if __name__ == '__main__':
    main()
