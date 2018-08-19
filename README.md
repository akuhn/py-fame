# A little language for schema-enforced models

Fame is a framework for metamodelling in Python.

- Entities are described by models
- Models are described by metamodels
- Models have fields, derived fields and constraints
- Entities can have custom fields
- Entities can be created even if data is invalid
- There are functions to validate and get all errors
- Validation checks presence and type of fields
- Validation checks all constraints
- Derived fields are memoized

Example

    class Experiment(Model):

        @schema
        def metamodel(self, m):
            m.field('name', str)
            m.field('subject', options(
                'user',
                'visitor',
                'email',
                'listing',
                'market'
            ))
            m.field('treatments', array(str))
            m.field('percent_exposed', int, default=100)
            m.field('design', nullable(str))

        @derived_field
        def is_miscellanous(self):
            return self.subject not in ['user', 'visitor']

        @constraint("expected percent_exposed to not exceed 100, got {}")
        def constraint(self):
            if self.percent_exposed > 100:
                return self.percent_exposed

Conventions

    - Define metamodel function first
    - Then define derived field functions
    - Then define all the constraint functions
    - Constraint functions are all named "constraint", that is intentional


## Installation

To install this package, run

    pip install fame


## Contributing

Bug reports and pull requests are welcome on github at, https://github.com/akuhn/py-fame
