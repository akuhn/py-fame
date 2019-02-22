from matchers import as_matcher


most_recent_metamodel = None
class Metamodel(object):

    # Metamodels are initialized through a double trigger,
    #
    # - Upon importing a module, the @schema decoration triggers __init__
    # - And later, accessing the decorated attribute triggers __get__
    #
    # The __init__ function is called once and only once per model class. It is
    # called when importing the module with the class definition and creates an
    # uninitialized instance of Metamodel that is stored in the python class as
    # as decorator of the metamodel attribute.
    #
    # The __get__ function is called once for each model instance. On the first
    # access to the metamodel attribute of an instance, this function is called
    # and then memoizes the metamodel attribute to optimize further calls. Upon
    # the very first access across all instances of a class, the initialization
    # of the Metamodel instance is finished by calling the decorated metamodel
    # function and then disposing of that initialization code.

    def __init__(self, function):
        global most_recent_metamodel
        assert function.__name__ == 'metamodel'
        self.pending_initialization = function
        self.constraints = []
        most_recent_metamodel = self

    def __get__(self, instance, cls):
        if self.pending_initialization: self.finish_initialization(cls)
        receiver = instance or cls
        setattr(receiver, 'metamodel', self) # memoize this attribute
        return self

    def finish_initialization(self, model):
        self.name = model.__name__
        self.fields = {}
        self.pending_initialization(None, self)
        self.derived_fields = {
            name: each
            for name, each in model.__dict__.items()
            if isinstance(each, DerivedField)
        }
        self.pending_initialization = None

    def field(self, field_name, field_type, **options):
        self.fields[field_name] = Field(field_name, field_type, **options)

    def get_field_value(self, entity, field_name, strict):
        if field_name in self.fields: return self.fields[field_name].get_value(entity)
        if field_name in self.derived_fields: return self.derived_fields[field_name].get_value(entity)
        if strict: object.__getattribute__(entity, field_name) # raises AttributeError
        return entity.data.get(field_name)

    def error_messages_prefix(self, entity):
        if 'name' in self.fields:
            return "{} '{}'".format(self.name, entity.name)
        else:
            return "{} at {}".format(self.name, hex(id(entity)))

    def error_messages(self, entity):
        for field in self.fields.values():
            value = field.get_value(entity)
            if not field.match(value):
                prefix = self.error_messages_prefix(entity)
                yield "{} expected field '{}' to be {}, got {}".format(prefix, field.name, field.match, value)
        for constraint in self.constraints:
            error_message = constraint.error_message(entity)
            if error_message:
                prefix = self.error_messages_prefix(entity)
                yield "{} {}".format(prefix, error_message)

    def __repr__(self):
        return "<Metamodel name={}>".format(self.name)

class Model(object):

    def __init__(self, **data):
        self.data = dict(data)

    def __getattr__(self, field_name):
        value = self.metamodel.get_field_value(self, field_name, strict=True)
        setattr(self, field_name, value) # memoize this attribute
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

    @classmethod
    def options_for(self, fieldname):
        return self.metamodel.fields[fieldname].match.options


class Field(object):

    def __init__(self, name, type_declaration, default=None, **options):
        self.name = name
        self.match = as_matcher(type_declaration)
        self.default = default
        self.options = options

    def get_value(self, entity):
        value = entity.data.get(self.name)
        return self.default if value is None else value

    def __repr__(self):
        return "<Field name={} type={}>".format(self.name, self.type_matcher)


class DerivedField(object):

    def __init__(self, function):
        self.name = function.__name__
        self.initializer = function

    def __get__(self, obj, cls):
        value = self.get_value(obj)
        setattr(obj, self.name, value) # memoize this attribute
        return value

    def get_value(self, entity):
        if self.name not in entity.data:
            value = self.initializer(entity)
            entity.data[self.name] = value
        return entity.data[self.name]

    def __repr__(self):
        return "<DerivedField name={}>".format(self.name)


class Constraint(object):

    # Constraints are initialized through a double trigger,
    #
    # - Upon importing a module, the @constraint decoration triggers __init__
    # - And immediately thereafter, python also triggers __call__
    #
    # Both functions are triggered once and only once per constraint, they are
    # called when importing the module with the class definition that contains
    # the constraint definition. We intercept python's creation of a new method
    # and instead wrap the decorated function into a Constraint instance, and
    # then append that constraint to the most recently defined metamodel.
    #
    # This is not most pythonic, but we rather prefer an API where constraints
    # are named after their error message string, as inspired by Rspec examples,
    # rather than forcing people to repeat themselves in the method name.

    def __init__(self, message):
        self.message = message

    def __call__(self, function):
        assert function.__name__ == 'constraint'
        self.function = function
        # Assume metamodel has been declared lexically above this
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

