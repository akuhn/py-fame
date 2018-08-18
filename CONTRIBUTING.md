# Contributing

Bug reports and pull requests are welcome on github at, https://github.com/akuhn/py-fame

# Deployment

To build this package, run

    brew install pandoc
    pip install pypandoc
    python setup.py sdist

For my personal use, to deploy this package, run

    # Requires accounts on pypi
    # Requires .pypirc file in home folder
    twine upload -r test dist/fame-0.0.0.tar.gz
    pip install --user -i https://testpypi.python.org/pypi fame
    open https://test.pypi.org/project/fame
    # Verify readme and package, and then continue with
    twine upload dist/fame-0.0.0.tar.gz
