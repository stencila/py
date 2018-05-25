from setuptools import setup

setup(
    name='stencila',
    version='0.28.1',

    description='Stencila for Python',
    long_description='''
        Stencila is the office suite for reproducible research.
        This package lets you create execution contexts for Python, and other languages, to use in Stencila Desktop or 
        your web browser.
    ''',

    author='Nokome Bentley',
    author_email='nokome@stenci.la',

    url='https://github.com/stencila/py',
    license='Apache-2.0',

    packages=[
        'stencila'
    ],

    include_package_data=True,

    install_requires=[
        'matplotlib',
        'numpy',
        'pandas',
        'six',
        'sphinxcontrib-napoleon',
        'werkzeug'
    ]
)
