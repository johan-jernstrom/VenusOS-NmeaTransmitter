#!/bin/sh

# set permissions
chmod -R 777 /data/VenusOS-NmeaTransmitter/

# create a symlink to the service directory to make it start automatically by the daemon manager
ln -s /data/VenusOS-NmeaTransmitter/service /service/VenusOS-NmeaTransmitter
ln -s /data/VenusOS-NmeaTransmitter/service /opt/victronenergy/service/VenusOS-NmeaTransmitter

echo "Service symlink created"

# start service
svc -t /service/VenusOS-NmeaTransmitter
echo "Service started"