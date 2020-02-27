import setuptools


setuptools.setup(
    name='booktag-a1black',
    version='0.0.1',

    author='a1black',
    description='A simple script for fill in the tags in an audio book.',
    license='GPLv2',
    url='https://github.com/a1black/booktag',
    classifiers=[
        'Environment :: Console',
        'Intended Audience :: End Users/Desktop',
        'Topic :: Multimedia :: Sound/Audio',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Multimedia :: Sound/Audio'
    ],
    keywords='metadata, tagging, audio',

    packages=['booktag', 'booktag.commands'],
    python_requires='>=3.6',
    include_package_data=True,
    install_requires=[
        'humanize>=0.5.0',
        'mutagen>=1.43.0',
        'natsort>=6.2.0',
        'Pillow>=6.2.0',
        'psutil>=5.6.0',
        'python-magic>=0.4.15',
        'ruamel.yaml>=0.16.5',
        'tqdm>=4.43.0',
    ],

    entry_points={
        'console_scripts': [
            'btag=booktag.__main__:main'
        ]
    }
)
