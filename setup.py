from distutils.core import setup

try:
    import pypandoc
    long_description = pypandoc.convert('README.md', 'rst')
except:
    long_description = None


setup(
    name = 'fame',
    packages = ['fame'],
    version = '1.2.0',
    description = 'A little language for schema-enforced models.',
    long_description = long_description,
    author = 'Adrian Kuhn',
    author_email = 'akuhnplus@gmail.com',
    url = 'https://github.com/akuhn/py-fame',
)


# Change log
#
# 1.2.0
#
# - Fix metamodel class property, Example.metamodel
# - New class method, Example.options_for(field_name)
# - New type matcher, anything
# - New type matcher, reserved
#
# Prehistory starts here...
#
#
