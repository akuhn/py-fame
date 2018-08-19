from matchers import as_matcher


most_recent_metamodel = None
class Metamodel(object):

    def __init__(self, function):
        global most_recent_metamodel
        assert function.__name__ == 'metamodel'
        self.initializer = function
        self.constraints = []
        most_recent_metamodel = self

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
        self.initialize

    def initialize(self):
        pass

    def __getattr__(self, field_name):
        value = self.metamodel.get_field_value(self, field_name, strict=True)
        self.__dict__[field_name] = value
        return value

    def __getitem__(self, field_name):
        return self.metamodel.get_field_value(self, field_name, strict=False)

    def is_valid(self):
        return not any(self.metamodel.error_messages(self))

    def error_messages(self):
        return list(self.metamodel.error_messages(self))

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

    def __init__(self, function):
        self.name = function.__name__
        self.initializer = function

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

    def __init__(self, message):
        self.message = message

    def __call__(self, function):
        assert function.__name__ == 'constraint'
        self.function = function
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

