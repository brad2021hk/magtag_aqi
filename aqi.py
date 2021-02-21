import time
from adafruit_magtag.magtag import MagTag
from secrets import secrets

magtag = MagTag()

# /////////////////////////////////////////////////////////////////////////

def get_current_AQI():

    '''Info to get airnow token and see data format:  https://docs.airnowapi.org/'''
    URL = "https://www.airnowapi.org/aq/observation/zipCode/current/?format=application/json&zipCode="
    URL += secrets["zipcode"]
    URL += "&API_KEY="
    URL += secrets["airnow_token"]

    resp = magtag.network.fetch(URL)
    json_data = resp.json()

    # Initialize Data
    o3_value = 0
    o3_category = "No Data"
    pm2p5_value = 0
    pm2p5_category = "No Data"
    curr_hour = "No Data"

    ''' The Air Now site returns between 0 and 2 data sets.  It can return o3 and pm2.5
    in any order.  It can also return no elements or just one of them.  At first, the
    code expected to get both elements, and randomly failed.  I now iterate through the
    array of returned data.  Check which one is returned and set the variables.  If no
    data is returned, the initialized data above is used.  There is a hole in this in
    cases where Air Now returns data for multiple locations.  The last location will be
    stored in the variables.  That may not be ideal.  For my zip code, it seems to work.'''
    for element in json_data:
        curr_hour = element['HourObserved']
        if (element['ParameterName'] == "O3"):
            o3_value = element['AQI']
            o3_category = element['Category']['Name']
        elif (element['ParameterName'] == "PM2.5"):
            pm2p5_value = element['AQI']
            pm2p5_category = element['Category']['Name']

    return o3_value, o3_category, pm2p5_value, pm2p5_category, curr_hour

def analyze_results(o3_data="No Data", pm2p5_data="No Data", curr_hour="No Data", status="No Data"):

    '''Look for scenarios where no network connection was possible or an empty set of data was returned
    Will setup a retry in 5 minutes.'''
    if (status == "No Network"):
        return "No Network", 300

    if (curr_hour == "No Data"):
        return "No Data", 300

    """Enter deep sleep for time needed. I explored using the time returned as part of the algorithm
    for setting sleep time. Basically to not update over night and save battery. The HourObserved
    value was somewhat disconnected from the hour data is fetched, causing weird behavior in the
    morning. I could make that reliable by fetching time from a separate data source. The energy cost
    probably exceeds the cost of checking air quality data more frequently. Instead I basically checking
    every 2 hours when the air quality is good and every 30 minutes when it isn't. Recommend changing these
    to suit your battery life needs and sensitivity to timely data."""
    if ((o3_data > 50) or (pm2p5_data > 50)):
        seconds_to_sleep = 1800
    else:
        seconds_to_sleep = 7200

    return "Complete", seconds_to_sleep

def go_to_sleep(seconds_to_sleep):
    print(
        "Sleeping for {} hours, {} minutes".format(
            seconds_to_sleep // 3600, (seconds_to_sleep // 60) % 60
        )
    )
    magtag.exit_and_deep_sleep(seconds_to_sleep)

# ===========
#  M A I N
# ===========

print("Updating...\n")

'''The network fetch is not 100% reliable.  I added "try" and "except" to handle cases
where the network connection fails. I know using a bare except is not ideal. In this
IOT application, I'm not super worried about user input.'''
try:
    o3_data, o3_category, pm2p5_data, pm2p5_category, curr_hour = get_current_AQI()
except:
    status = "No Network"
    status, next_update = analyze_results(status=status)
else:
    status = "Fetch Complete"
    status, next_update = analyze_results(o3_data, pm2p5_data, curr_hour, status)

if ((status == "No Data")or(status == "No Network")):
    magtag.add_text(
    text_position=(
        10,
        (magtag.graphics.display.height // 2) - 30,
    ),
    text_scale=1,
    text_anchor_point=(0, 0),
    )
    magtag.set_text(("{}, Sleeping {} minutes".format(status, next_update//60)), 0, False)
else:
    magtag.add_text(
        text_position=(10, 0
            # (magtag.graphics.display.width // 2) - 20,
            # (magtag.graphics.display.height // 2) - 20,
        ),
        text_scale=1,
        text_anchor_point=(0, 0),
    )
    magtag.set_text(("Last Updated {}:00  Next Update in {} minutes".format(curr_hour, next_update//60)), 0, False)

    magtag.add_text(
        text_position=(
            10,
            (magtag.graphics.display.height // 2) - 30,
        ),
        text_scale=2,
        text_anchor_point=(0, 0),
    )

    magtag.set_text(("PM2.5:{:4} {}".format(pm2p5_data, pm2p5_category)), 1, False)
    magtag.add_text(
        text_position=(
            10,
            (magtag.graphics.display.height // 2),
        ),
        text_scale=2,
        text_anchor_point=(0, 0),
    )
    magtag.set_text("Ozone:{:4} {}".format(o3_data, o3_category), 2, False)

    magtag.add_text(
        text_position=(
            10,
            (magtag.graphics.display.height)-15,
        ),
        text_scale=1,
        text_anchor_point=(0, 0),
    )
    magtag.set_text("Battery Level: {:.2f}".format(magtag.peripherals.battery), 3, False)

time.sleep(magtag.display.time_to_refresh + 1)
magtag.display.refresh()
time.sleep(magtag.display.time_to_refresh + 1)

go_to_sleep(next_update)

