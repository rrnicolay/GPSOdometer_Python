An odometer algorithm that uses GPS (NMEA sentences).

The threshold parameters are optimized to compute distances traveled by a vehicle.

To execute:
- Navigate to the project folder.
- Type "python3 odometer.py <input_file.txt>"

Output:
- A html file with the used points shown on a map;
- A .png file with charts of the route.

Fields used:
- From GGA: latitude, longitude, fix quality and tracked satellites
- From RMC: speed and status
- From GSA: fix type and PDOP

GitHub repo to get NMEA samples:

https://github.com/esutton/gps-nmea-log-files
