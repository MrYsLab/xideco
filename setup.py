from distutils.core import setup

setup(
        name='xideco',
        version='0.1.0',
        packages=['xideco', 'xideco.data_files', 'xideco.data_files.port_map', 'xideco.data_files.configuration',
                  'xideco.data_files.scratch_files', 'xideco.data_files.scratch_files.projects',
                  'xideco.data_files.scratch_files.extensions', 'xideco.http_bridge', 'xideco.xideco_router',
                  'xideco.arduino_bridge', 'experiments'],
        install_requires=['pymata-aio>=2.8',
                      'aiohttp>=0.19.0',
                      'pyzmq>=15.1.0',
                      'umsgpack>=0.1.0'],
        package_data={'xideco.data_files': [('configuration/*'),
                            ('scratch_files/extensions/*.s2e'),
                            ('scratch_files/projects/*.sb2'),
                            ('Snap!Files/*.xml')]},
        entry_points={
        'console_scripts': [
            'xiab = xideco.arduino_bridge.xiab:arduino_bridge',
            'xihb = xideco.http_bridge.xihb:http_bridge',
            'xirt = xideco.xideco_router.xirt:xideco_router'
        ]
    },
    url='https://github.com/MrYsLab/xideco/wiki',
    download_url='https://github.com/MrYsLab/xideco',
    license='GNU General Public License v3 (GPLv3)',
    author='Alan Yorinks',
    author_email='MisterYsLab@gmail.com',
    description='A Network Enabled Software Backplane',
    keywords=['Firmata', 'Arduino', 'Scratch', 'ZeroMQ'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Other Environment',
        'Intended Audience :: Education',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.5',
        'Topic :: Education',
    ],
)
