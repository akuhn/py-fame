import re


def as_matcher(type_declaration):
    if type_declaration == str: type_declaration = basestring
    if isinstance(type_declaration, type): return TypeMatcher(type_declaration)
    return type_declaration


class TypeMatcher(object):

    def __init__(self, type):
        self.type = type

    def __call__(self, value):
        return isinstance(value, self.type)

    def __str__(self):
        return self.type.__name__


class ArrayMatcher(object):

    def __init__(self, type_declaration):
        self.match = as_matcher(type_declaration)

    def __call__(self, values):
        if not isinstance(values, list): return False
        return all(self.match(each) for each in values)

    def __str__(self):
        return "array({})".format(self.match)


class NullableMatcher(object):

    def __init__(self, type_declaration):
        self.match = as_matcher(type_declaration)

    def __call__(self, value):
        return (value is None) or self.match(value)

    def __str__(self):
        return "nullable({})".format(self.match)


class OptionsMatcher(object):

    def __init__(self, *strings):
        self.options = strings

    def __call__(self, value):
        return value in self.options

    def __str__(self):
        return "options{}".format(self.options)


class RegularExpressionMatcher(object):

    def __init__(self, pattern):
        self.regexp = re.compile(pattern)

    def __call__(self, value):
        if not isinstance(value, basestring): return False
        return self.regexp.search(value)

    def __str__(self):
        return "regexp({})".format(self.regexp.pattern)


class AnythingMatcher(object):

    def __call__(self, value):
        return True

    def __str__(self):
        return 'anything'


class ReservedMatcher(object):

    def __call__(self, value):
        return False

    def __str__(self):
        return 'reserved'

