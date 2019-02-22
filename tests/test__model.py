from expects import *

from fame import array
from fame import constraint
from fame import derived_field
from fame import nullable
from fame import options
from fame import regexp
from fame import schema
from fame import Model


class Example(Model):

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
        m.field('design', nullable(regexp("^https?://")))

    @derived_field
    def is_miscellanous(self):
        return self.subject not in ['user', 'visitor']

    @derived_field
    def callonce(self):
        if hasattr(self, 'sentinel'): raise RuntimeError, 'expected to be called once, called twice'
        self.sentinel = True
        return True

    @constraint("expected percent_exposed to not exceed 100, got {}")
    def constraint(self):
        if self.percent_exposed > 100:
            return self.percent_exposed


class Broken(Model):

    @schema
    def metamodel(self, m):
        pass

    @constraint("exepected to not return {}")
    def constraint(self):
        return False

    @constraint("exepected to not return {} and {}")
    def constraint(self):
        return 'foo', 'bar'



def test____should_all_have_same_metamodel():
    m1 = Example()
    m2 = Example()

    expect(m1).to_not(be(m2))
    expect(m1.metamodel).to(be(m2.metamodel))


def test____should_have_one_constraint():
    m = Example()

    expect(m.metamodel.constraints).to(have_length(1))
    expect(m.metamodel.fields).to(have_length(5))
    expect(m.metamodel.derived_fields).to(have_length(2))


def test____should_validate_model():
    m = Example(
        name='button_color',
        subject='user',
        treatments='control treatment'.split(),
        whatnot='gibberish',
    )

    expect(list(m.error_messages())).to(be_empty)
    expect(m.is_valid()).to(be_true)


def test____should_get_fields_as_attributes():
    m = Example(name='button_color', subject='user', whatnot='gibberish')

    expect(m.name).to(equal('button_color'))
    expect(m.subject).to(equal('user'))
    expect(m.percent_exposed).to(equal(100))
    expect(lambda: m.whatnot).to(raise_error(AttributeError))
    expect(lambda: m.covfefe).to(raise_error(AttributeError))


def test____should_get_fields_as_items():
    m = Example(name='button_color', subject='user', whatnot='gibberish')

    expect(m['name']).to(equal('button_color'))
    expect(m['subject']).to(equal('user'))
    expect(m['percent_exposed']).to(equal(100))
    expect(m['whatnot']).to(equal('gibberish'))
    expect(m['covfefe']).to(be_none)


def test___should_not_validate():
    m = Example(name='button_color', percent_exposed=200, design=False)
    errors = list(m.error_messages())

    expect(m.is_valid()).to_not(be_true)
    expect(errors).to(contain(end_with("expected percent_exposed to not exceed 100, got 200")))
    expect(errors).to(contain(end_with("expected field 'treatments' to be array(basestring), got None")))
    expect(errors).to(contain(end_with("expected field 'subject' to be options('user', 'visitor', 'email', 'listing', 'market'), got None")))
    expect(errors).to(contain(end_with("expected field 'design' to be nullable(regexp(^https?://)), got False")))
    expect(errors).to(have_length(4))


def test____should_automagically_match_unicode():
    m = Example(name=u'gibberish', subject=u'user', treatments=[])
    errors = list(m.error_messages())

    expect(errors).to(be_empty)
    expect(m.is_valid()).to(be_true)


def test____should_get_dervied_fields_as_attributes():
    m = Example(name='button_color', subject='user')

    expect(m.subject).to(equal('user'))
    expect(m.is_miscellanous).to(equal(False))


def test____should_get_dervied_fields_as_items():
    m = Example(name='button_color', subject='user')

    expect(m['subject']).to(equal('user'))
    expect(m['is_miscellanous']).to(equal(False))


def test____should_memoize_fields():
    m = Example(subject='email')

    expect(m.subject).to(equal('email'))
    m.data = None # would raise error if accessed
    expect(m.subject).to(equal('email'))


def test____should_memoize_derived_fields():
    m = Example()

    expect(m.callonce).to(be_true)
    expect(m['callonce']).to(be_true)

    m = Example()

    expect(m['callonce']).to(be_true)
    expect(m.callonce).to(be_true)

    m = Example()

    expect(m['callonce']).to(be_true)
    expect(m['callonce']).to(be_true)

    m = Example()

    expect(m.callonce).to(be_true)
    m.data = None # would raise error if accessed
    expect(m.callonce).to(be_true)


def test____should_be_broken():
    m = Broken()
    errors = list(m.error_messages())

    expect(m.metamodel.constraints).to(have_length(2))
    expect(errors).to(contain(end_with("exepected to not return False")))
    expect(errors).to(contain(end_with("exepected to not return foo and bar")))
    expect(errors).to(have_length(2))


def test____should_not_match_regexp():
    m = Example(design='covfefe')

    expect(m.error_messages()).to(contain(end_with(
        "expected field 'design' to be nullable(regexp(^https?://)), got covfefe"
    )))


def test____number_should_not_match_regexp():
    m = Example(design=9000)

    expect(m.error_messages()).to(contain(end_with(
        "expected field 'design' to be nullable(regexp(^https?://)), got 9000"
    )))


def test____should_have_options_for():
    options = ('user', 'visitor', 'email', 'listing', 'market')

    expect(Example.options_for('subject')).to(equal(options))


def test____should_have_metamodel():
    m = Example()

    expect(Example).to(have_property('metamodel'))
    expect(Example.metamodel).to(equal(m.metamodel))

