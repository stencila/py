from setuptools import setup

setup(
    name='stencila',
    version='0.1.0',

    description='Stencila Documents, Sheets, Contexts and Sessions for Python',
    long_description='''
        Stencila is a platform for creating, collaborating on, and publishing
        data driven documents.
    ''',

    author='Nokome Bentley',
    author_email='nokome@stenci.la',

    url='https://github.com/stencila/py',
    license='Apache-2.0',

    packages=[
        'stencila',
        'stencila/helpers',
        'stencila/servers',
        'stencila/utilities'
    ],

    install_requires=[
        'cssselect',
        'lxml',
        'pyaml',
        'pyyaml',
        'requests',
        'six',
        'werkzeug',
    ]
)
