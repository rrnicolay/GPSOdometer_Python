import sys
import os
import pynmea2
import math
import gmplot
import matplotlib.pyplot as plt
from dataclasses import dataclass
from dataclasses import fields

DEBUG_SHOW_DECODED_SENTENCES = False

# These are the threshold settings used by the algorithm
# Changing this settings leads to a different distance result
MIN_SPEED = 7
MIN_DISTANCE = 10
MAX_PDOP = 2.5
MAX_ACCURACY = 12

@dataclass
class SingleCoordinate:
  status: str = 'V'
  speed: float = 0.0
  lat: float = 0.00
  lon: float = 0.00
  fixQuality: int = 0
  trackedSat: int = 0
  pdop: int = 0
  alt: int = 0
  fixType: int = 1

# Total computed distance
gTotalDist = 0

# Stats: number of coordinates used after fix
gSkipped = 0
gUsed = 0

# Used to plot on GMaps
latitude_list = []
longitude_list = []

# Charts data
speedChart = []
pdopChart = []
altChart = []
trackedSatChart = []


def main():
  filepath = sys.argv[1]

  if not os.path.isfile(filepath):
    print("Please pass a file with NMEA sentences as parameter. Exiting...")
    sys.exit()

  # Parse all NMEA sentences
  with open(filepath) as fp:
    curCoordinate = SingleCoordinate()
    prevCoordinate = SingleCoordinate()

    for sentence in fp:
      coordinateCompleted = parseNMEA(curCoordinate, sentence)

      if(coordinateCompleted):
        updateOdometer(curCoordinate, prevCoordinate)
        curCoordinate = SingleCoordinate()
  
  # Compute and show results
  computeResults()


def updateOdometer(curCoor, prevCoor):
  global gTotalDist
  global gSkipped
  global gUsed

  # If had a previous fix
  if(prevCoor.lat != 0 and prevCoor.lon != 0):
    # computes distance increment from previous coordinate
    distIncrement = haversine(prevCoor.lat, prevCoor.lon, curCoor.lat, curCoor.lon)

    # Here the thresholds are applied to compute a distance increment
    if(shouldIncrementDistance(curCoor, distIncrement)):

      # Increment distance
      gTotalDist += distIncrement
      # Update prevCoor
      for field in fields(SingleCoordinate):
        setattr(prevCoor, field.name, getattr(curCoor, field.name))

      # Increment used coordinates
      gUsed = gUsed + 1

      # Add data to plot on map
      latitude_list.append(curCoor.lat)
      longitude_list.append(curCoor.lon)

      # Add data to charts arrays
      speedChart.append(float(curCoor.speed))
      pdopChart.append(float(curCoor.pdop))
      trackedSatChart.append(int(curCoor.trackedSat))
      altChart.append(float(curCoor.alt))
    else:
      gSkipped = gSkipped + 1

  else:
    # First fix
    if(hasFix(curCoor)):
      for field in fields(SingleCoordinate):
        setattr(prevCoor, field.name, getattr(curCoor, field.name))


# Returns True if GPS has fixed its position
def hasFix(curCoor):
  return (curCoor.status == 'A' and\
        int(curCoor.fixQuality) > 0 and\
        int(curCoor.fixType) > 1)


# Returns True if triggered the thresholds to distance increment
def shouldIncrementDistance(curCoor, distIncrement):
  return (hasFix(curCoor) and \
      (float(curCoor.speed) >= MIN_SPEED or distIncrement >= MIN_DISTANCE) and\
      float(curCoor.pdop) <= MAX_PDOP)


def computeResults():
  print("\nTotal distance: %.4fKm" % float(gTotalDist/1000))
  print("Points used: %d" % (gUsed))
  print("Points skipped: %d\n"% (gSkipped))

  if(gUsed == 0):
    return

  # Creates a map of the trip starting from first coordinates
  # Last param is the zoom level
  gmap3 = gmplot.GoogleMapPlotter(latitude_list[0], longitude_list[0], 17)
  gmap3.scatter(latitude_list, longitude_list, '# FF0000', size = 1, marker = False)
  # Plot a line between coordinates
  gmap3.plot(latitude_list, longitude_list, 'cornflowerblue', edge_width = 1.0)
  # Saves to html
  gmap3.draw("trip.html")

  plt.figure(figsize=(19,10))

  # X axis data
  chartX = range(0, len(speedChart))

  CHART_NUM = 4
  plt.subplot(CHART_NUM, 1, 1)
  plt.plot(chartX, speedChart, '-')
  plt.ylabel('Speed [Km/h]')

  plt.subplot(CHART_NUM, 1, 2)
  plt.plot(chartX, pdopChart, '-')
  plt.ylabel('PDOP')

  plt.subplot(CHART_NUM, 1, 3)
  plt.plot(chartX, trackedSatChart, '-')
  plt.ylabel('Tracked Sat. [Units]')

  plt.subplot(CHART_NUM, 1, 4)
  plt.plot(chartX, altChart, '-')
  plt.ylabel('Alt [m]')

  plt.savefig("chart.png")


# Uses pynmea2 to parse NMEA sentences
def parseNMEA(curCoor, cmd):
  isCoordinateComplete = False

  if cmd.find('GGA') > 0:
    msg = pynmea2.parse(cmd)
    try:
      curCoor.lat = float(msg.latitude) # in decimal degrees
      curCoor.lon = float(msg.longitude) # in decimal degrees
      curCoor.fixQuality = int(msg.gps_qual)
      curCoor.trackedSat = int(msg.num_sats)
      curCoor.alt = float(msg.altitude)

      if(DEBUG_SHOW_DECODED_SENTENCES):
        print("[GGA] Timestamp: {}, Lat: {} {}, Lon: {} {}, Fix Quality:\
          {}, HDOP: {}, Altitude: {} {}, Satellites: {}".format(msg.timestamp, \
          msg.latitude, msg.lat_dir, msg.longitude, msg.lon_dir,\
          msg.gps_qual, msg.horizontal_dil, msg.altitude, msg.altitude_units,\
          msg.num_sats))
    
    except:
      curCoor.lat = 0.0
      curCoor.lon = 0.0
      curCoor.alt = 0.0
      curCoor.fixQuality = 0
  
  if cmd.find('RMC') > 0:
    try:
      msg = pynmea2.parse(cmd)
      curCoor.status = msg.status
      # Multiply by 1.852 to convert to km/h
      curCoor.speed = float(msg.spd_over_grnd)*1.852

      if(DEBUG_SHOW_DECODED_SENTENCES):
        print("[RMC] Timestamp: {}, Status: {}, Lat: {} {}, Lon: {} {}, Speed: {}"\
          .format(msg.timestamp, msg.status, msg.latitude, msg.lat_dir,\
            msg.longitude, msg.lon_dir, msg.spd_over_grnd))
    except:
      curCoor.speed = 0
      curCoor.status = 'V'
    
    # When a RMC arrived, consider that all the sentences that 
    # represents a single coordinate has been received.
    isCoordinateComplete = True
  
  if cmd.find('GLL') > 0:
    msg = pynmea2.parse(cmd)

    if(DEBUG_SHOW_DECODED_SENTENCES):
      print("[GLL] Timestamp: {}, Status: {}, Lat: {} {}, Lon: {} {}"\
        .format(msg.timestamp, msg.status, msg.latitude, msg.lat_dir,\
          msg.longitude, msg.lon_dir))

  if cmd.find('GSA') > 0:
    msg = pynmea2.parse(cmd)
    try:
      curCoor.fixType = int(msg.mode_fix_type)
      curCoor.pdop = float(msg.pdop)

      if(DEBUG_SHOW_DECODED_SENTENCES):
        print("[GSA] Mode: {}, Fix Type: {}, PDOP: {}".format(msg.mode,\
          msg.mode_fix_type, msg.pdop))

    except:
      curCoor.fixType = 1
      curCoor.pdop = 100.0
  
  return isCoordinateComplete


# Computes the distance between two coordinates considering that Earth
# is a sphere (yeah, it isnt flat).
# Maybe, because the points are asually very close from each other,
# we could use a simpler approach (single trigonometry).
def haversine(lat1, lon1, lat2, lon2):
  R = 6372800  # Earth radius in meters

  phi1, phi2 = math.radians(lat1), math.radians(lat2)
  dphi       = math.radians(lat2 - lat1)
  dlambda    = math.radians(lon2 - lon1)

  a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2

  return 2*R*math.atan2(math.sqrt(a), math.sqrt(1 - a))


if __name__ == '__main__':
  main()
