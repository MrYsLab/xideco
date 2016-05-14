from setuptools import setup

setup(
        name='xideco',
        version='0.5.2',
        packages=['xideco', 'xideco.data_files', 'xideco.data_files.port_map', 'xideco.data_files.configuration',
                  'xideco.data_files.scratch_files', 'xideco.data_files.scratch_files.projects',
                  'xideco.data_files.scratch_files.extensions', 'xideco.http_bridge', 'xideco.xideco_router',
                  'xideco.arduino_bridge', 'xideco.raspberrypi_bridge','xideco.beaglebone_bridge',
                  'experiments', 'experiments.xideco_tweeter','xideco.i2c.i2c_devices.adxl345',
                  'xideco.xidekit'],
        install_requires=['pymata-aio>=2.8',
                          'aiohttp>=0.19.0',
                          'pyzmq>=15.1.0',
                          'umsgpack>=0.1.0'],
        package_data={'xideco.data_files': [('configuration/*'),
                                            ('scratch_files/extensions/*.s2e'),
                                            ('scratch_files/projects/*.sb2')]},
        entry_points={
            'console_scripts': [
                'xiab = xideco.arduino_bridge.xiab:arduino_bridge',
                'xihb = xideco.http_bridge.xihb:http_bridge',
                'xirt = xideco.xideco_router.xirt:xideco_router',
                'xirb = xideco.raspberrypi_bridge.xirb:raspberrypi_bridge',
                'xibb = xideco.beaglebone_bridge.xibb:beaglebone_bridge',
                'xibbi2c = xideco.beaglebone_bridge.xibbi2c:beaglebone_bridge'
            ]
        },
        url='https://github.com/MrYsLab/xideco/wiki',
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
            'Topic :: Software Development',
            'Topic :: Home Automation',
            'Topic :: System :: Hardware'
        ],
)
