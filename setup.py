import setuptools


setuptools.setup(
    name='booktag-a1black',
    package_dir={'': 'booktag'},
    packages=setuptools.find_namespace_packages(where='booktag'),
    version='0.1dev0',

    author='a1black',
    description='A simple script for fill in the tags in an audio book.',
    license='GPLv2',
    url='https://github.com/a1black/booktag',
    classifiers=[
        'Environment :: Console',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: MIT License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Multimedia :: Sound/Audio'
    ],

    python_requires='>=3.6',
    install_requires=[
        'mutagen>=1.40.0',
        'Pillow>=6.0.0',
        'python-magic>=0.4.0',
        'urwid>=2.0.1'
    ]
)
