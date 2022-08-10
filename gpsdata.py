import random
import time
import json
from datetime import datetime
import os

from paho.mqtt import client as mqtt_client
from gpsdclient import GPSDClient

"""
*** Hardware Setup ***
1. 2 Raspberry pi's, one with Home Assistant running on it, second one has the GPS receiver attached
2. GPS receiver
3. On the RPI with the gps receiver attached, install gpsd and gpsdclient

*** Functionailty ***
This code will listen for events from a GPSD client (in my case a GPS receiver plugged into raspberry pi 3b+)
It will then send the latitude and longitude coordinates along with some other gps data to 
home assistant via MQTT which is on my seperate raspberry pi 4.

This code triggers from a Cron task and records a successful outcome or a failure in a file called /home/pi/crontasks.log
Use the command "cat /home/pi/crontasks.log" to view the contents of the log file once up and running or use
 "journalctl" commnd to view errors
 
TIPS: Read through the below code. Lines that start with "todo" indicate things you need to customise, such as add your MQTT 
ip address etc.
Lines starting with # are comments to assist working out what the relevant code does.

NOTE: 
Print messages in this code won't display during a cron task. To see print messages run this file manually from the command
 line. EG: `python3 gpsdata.py`

*** Home Assistant set up in configuration.yaml ***
mqtt:
  device_tracker:
    - name: "Caravan GPS receiver"
      state_topic: "homeassistant/caravan_gps_receiver/state"
      json_attributes_topic: "homeassistant/caravan_gps_receiver/attributes"
      json_attributes_template: "{{ value_json | tojson}}"

* NOTE - Obviously change caravan_gps_receiver to the same topic name you used in the below "configTopic" and "attrTopic". 
and restart HA after editing the file

*** Home Assistant Automation ***
Create a automation that triggers on a MQTT topic of "homeassistant/your_device_name/attributes". Once triggered use the set.location service
 as the action, as per below example.

 service: homeassistant.set_location
data_template:
  latitude: "{{ states.device_tracker.your_device_name.attributes.latitude }}"
  longitude: "{{ states.device_tracker.your_device_name.attributes.longitude }}"

*** Lastly, create the Cron task ***

In the terminal of the RPI with the receiver attached. type "crontab -e" and push enter.
at the end of the file that opens add...

*/1 * * * * /usr/bin/python3 /home/pi/gpsdata.py

then save the file and the cron task will run. (in this case every minute). However, you can change it to every 15 minutes or what ever
for example by changing 
*/1 in the above line to */15 or read the crontab file to see what to change for various days months, hours etc

Last NOTE: Log file will get deleted at 50MB and start again. That way the log file won't get infinately big 
and use up un nessasary storage space 
"""

# todo - Change the below configureable items to suit your MQTT details.

## Configure these
mqttBroker = '192.168.1.44'
mqttPort = 1883
mqttUsername = 'Your MQTT Username'
mqttPassword = 'Your MQTT password'
deviceName = 'caravan_gps_receiver'
## configuration end

# The MQTT topics, no need to modify
mqttTopic = f"homeassistant/{deviceName}"


# generate client ID with pub prefix randomly
client_id = f'gpsdata-{random.randint(0, 1000)}'


logPayload = False # Change this to True if you want to see the raw gpsd data in the log file for reference purposes

# The path to the log file
filePath = '/home/pi/crontasks.log'
logSizeLimit = 50 # Sets the log file sizelimit in MB

# MQTT Connection method
def connect_mqtt():

    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker!........")
        else:
            print("Failed to connect, return code %d\n", rc)
    client = mqtt_client.Client(client_id)
    client.username_pw_set(mqttUsername, mqttPassword)
    client.on_connect = on_connect
    client.connect(mqttBroker, mqttPort)
    return client

# MQTT publish method. This method is responsible for sending the MQTT message to Home Assistant
def publish(client):
    attributePayload = getGpsdData() # This Sets "attributePayload" to what ever the result of getGpsdData returns (see method further down)

    if attributePayload is not None:
        time.sleep(1)

        # One of two messages that get sent to HA. This is the config payload and in general won't need modifying
        configPayload = {
            'state_topic': f"{mqttTopic}/state",
            "name": "GPS receiver",
            "payload_home": "home",
            "payload_not_home": "not_home",
            "json_attributes_topic": f"{mqttTopic}/attributes"
        }
        statePayload = 'home'


        # Publish attributes to the MQTT broker as a json
        result = client.publish(f'{mqttTopic}/attributes', json.dumps(attributePayload))
        # Publish HA configuration data to the MQTT broker as a json
        client.publish(f'{mqttTopic}/config', json.dumps(configPayload))
        # Publish State data via MQTT as JSON
        client.publish(f'{mqttTopic}/state', json.dumps(statePayload))

        # Check for successful MQTT delivery and log/display the result
        status = result[0]

        if status == 0 :
            print(f"Sent `{attributePayload}` to topic `{mqttTopic}/attributes`")
            print("")
            print(f'Also sent {configPayload} to {mqttTopic}/config ')
            print("")
            print(f"and the state of the tracker will be -->> {statePayload}")

            # The message to display in the log file if successfull/failed
            cronLogging(message='GPS Data was successfully sent')
        else:
            print(f"Failed to send messages to topic {mqttTopic}/attributes and/or {mqttTopic}/config")

            cronLogging(message='Failed to send GPS data')


def getGpsdData():
    client = GPSDClient(host="127.0.0.1") # This is where the GPSD client is running. 127.0.0.1 is the local
    # machine so you can usually leave this as it is

    # Create json payload
    for result in client.dict_stream():

        # if you've enabled payload logging, this statement will run
        if logPayload:
            cronLogging(message=result)

        # TPV class is where you longitude and latitude data is in the gpsd output
        if result["class"] == "TPV":

            # This gpsPayload is data you want sent to HA. replace/add/remove fields as required based on the output of your receiver
            # format is :
            # 'the name of the data field' : result["the name associated with the value that gpsd ouputs "]
            # my gpsd example output = {'class': 'TPV', 'device': '/dev/ttyACM0', 'status': 2, 'mode': 2, 'time': datetime.datetime(2022, 8, 10, 1, 38, 2), 'ept': 0.005, 'lat': -xx.351406667, 'lon': xxx.5549935, 'epx': 2.387, 'epy': 2.7, 'track': 0.0, 'speed': 0.09, 'eps': 5.4}
            gpsPayload = {
                'source_type': 'gps',
                'latitude': result["lat"],
                'longitude': result["lon"],
                'speed': result["speed"],
                #'ept': result["ept"],
                #'epx': result["epx"],
                #'epy': result["epy"],
                'track': result["track"],
                #'eps': result["eps"],
                'battery_level': 100
            }
            print("...............")
            print("")
            return gpsPayload

# Below creates log messages in a file called crontasks.log when a successful or failed cron job is completed
def cronLogging(message):
    currentTime = processTime()

    # check if log file is below 50mb, if not delete it and start fresh
    checkLogFileSize()

    mode = 'a' if os.path.exists(filePath) else 'w'
    with open(filePath, mode) as file:
        file.write(f'{currentTime} - {message} \n')

# This returns the timestamp to be used at the start of the log message
def processTime():
    now = datetime.now()
    currentTime = now.strftime("%H:%M:%S")
    return currentTime

# function that returns size of a file
def getFileSize(path):

    # getting file size in bytes
    actualFileSize = os.path.getsize(path)

    # returning the size of the file
    return actualFileSize


# function to delete a file
def removeLogFile(path):

    # deleting the log file
    if not os.remove(path):

        # success
        print(f"{path} is now deleted successfully due to exceeding file size limit of {logSizeLimit} ")

    else:

        # error
        print(f"Unable to delete {path}")


def checkLogFileSize():


    # checking whether the path exists or not
    if os.path.exists(filePath):

        # converting size to bytes
        limitSizeInBytes = logSizeLimit * 1024 * 1024


        # checking the filesize
        if getFileSize(filePath) >= limitSizeInBytes:
            # invoking the remove_file function
            removeLogFile(filePath)

        else:
            fileSizeInMB = getFileSize(filePath) / 1024 / 1024
            print("")
            print("Log file is still small enough to evade deletion")
            print(f"Actual size is {fileSizeInMB} MB ")
            print(f"Limit is {logSizeLimit} MB ")

    else:
        # path doesn't exist
        print(f"{filePath} doesn't exist")


def run():
    client = connect_mqtt()
    client.loop_start()
    publish(client)


if __name__ == '__main__':
    run()

