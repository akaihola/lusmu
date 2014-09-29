"""Tools for the Lusmu test suite

Copyright 2013 Eniram Ltd. See the LICENSE file at the top-level directory of
this distribution and at https://github.com/akaihola/lusmu/blob/master/LICENSE

"""


def parameterize(func):
    """Decorator for setting test function description based on arguments

    Example::

        def test_plus():

            @parameterize
            def check(a, b, expected):
                '''plus({0}, {1}) equals {2}'''
                assert plus(a, b) == expected

            yield check(1, 1, 2)
            yield check(2, 2, 4)

    """
    def get_test_call_info(*args):
        """Set test function description and return yieldable tuple"""
        if func.__doc__:
            func.description = func.__doc__.format(*args)
        else:
            func.description = func.__doc__
        return (func,) + args

    return get_test_call_info
