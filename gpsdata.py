import random
import time
import json
from datetime import datetime
import os

from paho.mqtt import client as mqtt_client
from gpsdclient import GPSDClient

"""
Instructions moved to ReadMe file

Code by Larry Shieffelbien
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
    currentTime = now.strftime("%c")
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

