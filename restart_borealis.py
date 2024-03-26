#!/usr/bin/python
# Copyright 2020 SuperDARN Canada, University of Saskatchewan
# Author: Kevin Krieger
"""
Python script to check data being written and restart Borealis in case it's not

Classes
-------

Methods
-------


References
----------


"""
import argparse
import os
import sys
import json
from datetime import timezone, timedelta, datetime as dt
import glob
import subprocess
import time

def send_email(last_data_write):
    # Define email parameters
    recipient_email = 'jordan.wiker@jhuapl.edu'
    subject = 'Borealis Check'

    # Format time since last data write
    time_since_last_write = timedelta(seconds=last_data_write)
    if time_since_last_write > timedelta(days=1):
        time_str = '{} days'.format(time_since_last_write.days)
    elif time_since_last_write.seconds >= 3600:
        hours = time_since_last_write.seconds // 3600
        time_str = '{} hours'.format(hours)
    else:
        minutes = time_since_last_write.seconds // 60
        time_str = '{} minutes'.format(minutes) if minutes > 0 else '{} seconds'.format(time_since_last_write.seconds)

    message = 'Borealis hasn\'t written new data in {}'.format(time_str)
    attachment_path = '/home/radar/logs/restart_borealis.log'

    # Construct the command
    #cmd = 'echo "{}" | mail -s "{}" -A "{}" "{}"'.format(message, subject, attachment_path, recipient_email)
    cmd = 'echo "{}" | mail -s "{}" "{}"'.format(message, subject, recipient_email)

    # Call the command using subprocess
    subprocess.call(cmd, shell=True, stdin=open(os.devnull, 'r'))

def get_args():
    """
    Supports the command-line arguments listed below.
    """
    parser = argparse.ArgumentParser(description="Borealis Check")
    parser.add_argument('-r', '--restart-after-seconds', type=int, default=300,
                        help='How many seconds can the data file be out of date before attempting '
                             'to restart the radar? Default 300 seconds (5 minutes)')
    parser.add_argument('-p', '--borealis-path', required=False, help='Path to Borealis directory',
                        dest='borealis_path', default='/home/radar/borealis/')
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    # Handling arguments
    args = get_args()
    restart_after_seconds = args.restart_after_seconds
    borealis_path = args.borealis_path

    if not os.path.exists(borealis_path):
        print("BOREALISPATH: {} doesn't exist".format(borealis_path))
        sys.exit(1)

    config_path = borealis_path + "/config.ini"
    try:
        with open(config_path) as config_data:
            raw_config = json.load(config_data)
            data_directory = raw_config["data_directory"]
    except IOError:
        print('Cannot open config file at {0}'.format(config_path))
        sys.exit(1)

    #####################################
    # Borealis data check               #
    #####################################

    # Get today's date and look for the current data file being written
    today = dt.utcnow().strftime("%Y%m%d")
    today_data_files = glob.glob("{}/{}/*".format(data_directory, today))
    # If there are no files yet today, then just use the start of the day as the newest file write time
    if len(today_data_files) == 0:
        new_file_write_time = dt.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        new_file_write_time = float(new_file_write_time.strftime("%s"))
    else:
        newest_file = max(today_data_files, key=os.path.getmtime)
        new_file_write_time = os.path.getmtime(newest_file)

    new_file_write_time = dt.utcfromtimestamp(new_file_write_time).replace(tzinfo=timezone.utc).astimezone(timezone.utc)
    new_file_write_time = float(new_file_write_time.strftime("%s"))

    now_utc_seconds = float(dt.utcnow().strftime("%s"))

    # How many seconds ago was the last write to a data file?
    last_data_write = now_utc_seconds - new_file_write_time
    print('Write: {}, Now: {}, Diff: {} s' 
          ''.format(dt.utcfromtimestamp(new_file_write_time).strftime('%Y%m%d.%H%M:%S'), 
                    dt.utcfromtimestamp(now_utc_seconds).strftime('%Y%m%d.%H%M:%S'),
                    last_data_write))

    # if under the threshold it is OK, if not then there's a problem
    print("{} seconds since last write".format(last_data_write))
    if float(last_data_write) <= float(restart_after_seconds):
        sys.exit(0)
    else:
        send_email(last_data_write) 

        # Now we attempt to restart Borealis
        stop_borealis = subprocess.Popen("{}/stop_radar.sh".format(borealis_path),
                                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = stop_borealis.communicate()
        # Check out the output to make sure it's all good (empty output means it's all good)
        if error:
            print('Attempting to restart Borealis: {}'.format(error))

        time.sleep(5)

        # TODO: Remove after scheduling is working
        script_directory = '/home/radar/borealis'
        os.chdir(script_directory)

        start_command = ['./steamed_hams.py', 'eclipsesound', 'release', 'common']
        process = subprocess.Popen(start_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()

        # Print the output
        print("Standard Output:")
        print(stdout.decode())

        # Print any errors
        if stderr:
            print("Errors:")
            print(stderr.decode())

        # Now call the start radar script, reads will block, so no need to communicate with
        # this process.
        #start_borealis = subprocess.Popen("{}/start_radar.sh".format(borealis_path),
        #                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # print('Borealis stop_radar.sh and start_radar.sh called')
        sys.exit(0)
