# Change Log

## Version 0.4.0

* Major Changes
    * Xideco Router was simplified to use a single ZeroMQ Forwarder.
    * The port_map.py file was simplified to reflect changes in router.
    * Implemented Universal i2c support.
        * Added i2c support to Arduino and Raspberry Pi Bridges.
        * Added i2c support to BeagleBone Black with new file, xibbi2c.py - requires use of Python 2.
        * Add a library class to support ADXL345 Accelerometer.
            * A sample program is provided to create a ZeroMQ data monitor for the ADXL345 class and is described [here](https://github.com/MrYsLab/xideco/wiki/ADXL345-Accelerometer). 
    * Updated FirmataPlus to be consistent with version 2.5.2 of StandardFirmata and is now included with distribution.
        * If you are using a previous version of FirmataPlus it should be replaced with the new version.
        * See [Wiki Page](https://github.com/MrYsLab/xideco/wiki/Uploading-FirmataPlus-to-Arduino) for instructions.
    * All modules were modified to allow setting the associated Xideco Router IP address via command line option


## Version 0.3.0

* BeagleBone Black support added.
* Scratch base projects were modified to use an alphanumeric field for pin numbers instead of numeric field.
* Arduino debug error codes were changed to offer a format consistent with the Raspberry Pi and BeagleBone codes.
* General code cleanup.

## Version 0.2.0

* Raspberry Pi support added.

## Version 0.1.0

* Initial release with Arduino support.