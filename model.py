from contrib import debug


# Defines a little language for schema-enforced models.
#
# - Entities are described by models
# - Models are described by metamodels
# - Models have fields, derived fields and constraints
# - Entities can have custom fields
# - Entities can be created even if data is invalid
# - There are functions to validate and get all errors
# - Validation checks presence and type of fields
# - Validation checks all constraints
# - Derived fields are memoized
#
# This is an improvement over our previous code. This allows us to untangle
# the config parser code and separate reading, transformation (for eg
# minerva integration), and validation into separate steps. Say goodbye to
# 300+ line constructors!
#
# For a discussion of implementation choices see,
# https://git.musta.ch/airbnb/data/pull/61695
#
# Example
#
#     class Example(Model):
#
#         @schema
#         def metamodel(self, m):
#             m.field('name', str)
#             m.field('subject', str)
#             m.field('percent_exposed', int, default=100)
#
#         @derived_field
#         def is_miscellanous(self):
#             return self.subject not in ['user', 'visitor']
#
#         @constraint("expected percent_exposed to not exceed 100, got {}")
#         def constraint(self):
#             if self.percent_exposed > 100:
#                 return self.percent_exposed
#
# Conventions
#
# - Define metamodel function first
# - Then define derived field functions
# - Then define all the constraint functions
# - Constraints are named "constraint," that is intentional
#
# Failover behavior
#
# - Forgotting to define the metamodel causes infinite recursion
# - Accessing self from within the metamodel function raises a null-pointer
#
# Usage
#
# See code examples in test__model.py


most_recent_metamodel = None
class Metamodel(object):

    # This function is called when sourcecode is imported. In python importing
    # sourcecode actually executes the file and thus this function is called on
    # the @schema line, and then this instance is used to wrap the decorated
    # metamodel property such that accessing it triggers __get__ below.
    def __init__(self, function):
        global most_recent_metamodel
        assert function.__name__ == 'metamodel'
        self.initializer = function
        self.constraints = []
        most_recent_metamodel = self

    # This functuion is called when first accessing the metamodel property of
    # an instance of a model class. On the first call per class, it initializes
    # the model's metamodel. On the first call per instance, it memoizes the
    # metamodel property.
    #
    # - entity = an instance of a model subclass
    # - model = the model subclass
    #
    def __get__(self, entity, model):
        if self.initializer: self.initialize_metamodel_once(model)
        entity.__dict__['metamodel'] = self
        return self

    def initialize_metamodel_once(self, model):
        self.name = model.__name__
        self.fields = {}
        self.initializer(None, self)
        self.derived_fields = {
            name: each
            for name, each in model.__dict__.items()
            if isinstance(each, DerivedField)
        }
        self.initializer = None

    def field(self, field_name, field_type, **options):
        self.fields[field_name] = Field(field_name, field_type, **options)

    def get_field_value(self, entity, field_name, strict):
        if field_name in self.fields: return self.fields[field_name].get_value(entity)
        if field_name in self.derived_fields: return self.derived_fields[field_name].get_value(entity)
        if strict: object.__getattribute__(entity, field_name) # raises AttributeError
        return entity.data.get(field_name)

    def error_messages(self, entity):
        if 'name' in self.fields:
            prefix = "{} '{}'".format(self.name, entity.name)
        else:
            prefix = "{} at {}".format(self.name, hex(id(entity)))
        for field in self.fields.values():
            value = entity.data.get(field.name)
            if not field.match(value):
                yield "{} expected field '{}' to be {}, got {}".format(prefix, field.name, field.type_matcher, value)
        for constraint in self.constraints:
            error_message = constraint.error_message(entity)
            if error_message:
                yield "{} {}".format(prefix, error_message)

    def __repr__(self):
        return "<Metamodel name={}>".format(self.name)

class Model(object):

    def __init__(self, **data):
        self.data = dict(data)

    def __getattr__(self, field_name):
        value = self.metamodel.get_field_value(self, field_name, strict=True)
        self.__dict__[field_name] = value
        return value

    def __getitem__(self, field_name):
        return self.metamodel.get_field_value(self, field_name, strict=False)

    def is_valid(self):
        return not any(self.error_messages())

    def error_messages(self):
        return self.metamodel.error_messages(self)

    @property
    def metamodel(self, m):
        raise NotImplementedError, "subclass must override metamodel"


class Field(object):

    def __init__(self, name, type_declaration, default=None, **options):
        self.name = name
        self.type_matcher = as_matcher(type_declaration)
        self.default = default
        self.options = options

    def match(self, value):
        if value is None: value = self.default
        return self.type_matcher(value)

    def get_value(self, entity):
        value = entity.data.get(self.name)
        return self.default if value is None else value

    def __repr__(self):
        return "<Field name={} type={}>".format(self.name, self.type_matcher)


class DerivedField(object):

    # This function is called when sourcecode is imported. In python importing
    # sourcecode actually executes the file and thus this function is called on
    # the @derived_field line, and then this instance is used to wrap the
    # decorated property such that accessing it trigger __get__ below.
    def __init__(self, function):
        self.name = function.__name__
        self.initializer = function

    # This functuion is called when accessing a derived field. On the first
    # call per instance, it memoizes the derived field.
    def __get__(self, entity, model):
        value = self.get(entity)
        entity.__dict__[self.name] = value
        return value

    def get_value(self, entity):
        if self.name not in entity.data:
            value = self.initializer(entity)
            entity.data[self.name] = value
        return entity.data[self.name]

    def __repr__(self):
        return "<DerivedField name={}>".format(self.name)


class Constraint(object):

    # This function is called when sourcecode is imported. In python importing
    # sourcecode actually executes the file and thus this function is called on
    # the @constraint line to create a decorator object and then ...
    def __init__(self, message):
        self.message = message

    # ... immediatly this function is called, where we intercept python's
    # creation of a new method and instead append this constraint to the model.
    # This is not most pythonic, but we rather prefer an API where constraints
    # are named after their error message (as inspired by rspec examples).
    def __call__(self, function):
        assert function.__name__ == 'constraint'
        self.function = function
        # Assume metamodel has been declared lexcially above this
        most_recent_metamodel.constraints.append(self)
        # Bind the attribute named 'constraint' to this class in order to make
        # sure we don't shadow the imported decorator named 'constraint'
        return Constraint

    def error_message(self, entity):
        values = self.function(entity)
        if values is None: return
        if not isinstance(values, tuple): values = (values,)
        return self.message.format(*values)

    def __repr__(self):
        return "<Constraint msg=\"{}\">".format(self.message)


# Matcher functions for field types

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
        self.strings = strings

    def __call__(self, value):
        return value in self.strings

    def __str__(self):
        return "options{}".format(self.strings)


# Export decorators and matchers as lowercase names

constraint = Constraint
derived_field = DerivedField
schema = Metamodel

array = ArrayMatcher
nullable = NullableMatcher
options = OptionsMatcher

