from distutils.core import setup

try:
    import pypandoc
    long_description = pypandoc.convert('README.md', 'rst')
except:
    long_description = None


setup(
    name = 'fame',
    packages = ['fame'],
    version = '1.1.0',
    description = 'A little language for schema-enforced models.',
    long_description = long_description,
    author = 'Adrian Kuhn',
    author_email = 'akuhnplus@gmail.com',
    url = 'https://github.com/akuhn/py-fame',
)
