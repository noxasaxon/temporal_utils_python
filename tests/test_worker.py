from temporalio import activity

from temporal_utils.collectors import (
    FunctionCategory,
    get_all_activity_methods_from_object,
    identify_function_category,
)


def test_get_all_activity_methods_from_instance_of_class():
    class TestClass:
        def __init__(self):
            pass

        @activity.defn
        async def act1(self):
            pass

        @activity.defn
        async def act2(self):
            pass

    test_instance = TestClass()
    all_activity_methods = get_all_activity_methods_from_object(test_instance)
    assert len(all_activity_methods) == 2
    assert all_activity_methods[0] == test_instance.act1
    assert all_activity_methods[1] == test_instance.act2


def test_get_all_activity_methods_from_object():
    class TestClass:
        def __init__(self):
            pass

        @activity.defn
        async def act1(self):
            pass

        @activity.defn
        async def act2(self):
            pass

    # test_instance = TestClass()
    all_activity_methods = get_all_activity_methods_from_object(TestClass)
    assert len(all_activity_methods) == 2
    assert all_activity_methods[0] == TestClass.act1
    assert all_activity_methods[1] == TestClass.act2


def test_identify_function_category():
    def regular_function():
        pass

    class RegularClass:
        def class_method(self, a: int, b: int):
            pass

    assert (
        identify_function_category(regular_function)
        == FunctionCategory.REGULAR_FUNCTION
    )
    assert (
        identify_function_category(RegularClass.class_method)
        == FunctionCategory.CLASS_METHOD
    )
    assert (
        identify_function_category(RegularClass().class_method)
        == FunctionCategory.CLASS_METHOD
    )
