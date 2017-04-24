from setuptools import setup

setup(
    name='stencila',
    version='0.1.0',

    description='Stencila for Python',
    long_description='''
        Stencila is a platform for creating, collaborating on, and publishing
        data driven documents.
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
        'werkzeug'
    ]
)
