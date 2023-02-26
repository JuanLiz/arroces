#!/bin/python

import datetime as dt
import json
import os
import subprocess
import sys

import todo
from dotenv import load_dotenv


def parse_date(date):
    '''
    Parse eww's date. Eww gives month from 0 to 11. To avoid errors using To Do
    API, month needs to be modified
    '''
    # If month is January, convert from 0 to 1
    if date[5] == '0':
        # Sum 1 to month
        month = int(date[5])+1
        newdate = date[:5]+'0'+str(month)+date[6:]
    # Other cases can be handled by datetime library
    else:
        newdate = dt.datetime.strptime(date, "%Y-%m-%dT%H:%M:%S.0")
        # Sum 1 to month
        newdate = newdate.replace(month=newdate.month+1)
        newdate = newdate.strftime("%Y-%m-%dT%H:%M:%S.0")

    return newdate


# Get client id from environment variables (.env file)
load_dotenv(
            dotenv_path=os.getenv('HOME')+'/.config/eww/dashboard/scripts/.env'
            )
CLIENT_ID = os.getenv('CLIENT_ID')

# Initialize authentication sending client_id
app = todo.initialize_auth(CLIENT_ID)

# First, try to get token from cache
auth = todo.get_token_from_cache(app)

# Return message if token isn't valid
if not auth:
    print('Token expired. You need to authenticate first')
    if sys.argv[1] == 'ping':
        pass
    # If there's no token, create device auth flow
    if sys.argv[1] == 'auth':
        auth = todo.authenticate(app)
# Read command args if token is valid
else:
    if sys.argv[1] == 'create':
        # Set loading state to true in eww
        os.system('eww update loading_form=true load_progress=25')
        # Check if duedate is specified
        if sys.argv[4] == 'true':
            os.system('eww update load_progress=50')
            date = parse_date(sys.argv[5])
            os.system('eww update load_progress=75')
            todo.create_task(auth, sys.argv[2], sys.argv[3], True, date)
        else:
            os.system('eww update load_progress=75')
            todo.create_task(auth, sys.argv[2], sys.argv[3])
        # Set loading state to false in eww and reset variables
        os.system("eww update load_progress=100 loading_form=false "
                  "taskform=false listid='' listname='' tasktitle='' "
                  "placeholder='' hasduedate=false duedate=false")

    if sys.argv[1] == 'complete':
        todo.complete_task(auth, sys.argv[2], sys.argv[3])

    if sys.argv[1] == 'update':
        # Set loading state to true in eww
        os.system('eww update loading_form=true load_progress=25')
        # Check if duedate is specified
        if sys.argv[5] == 'true':
            # Parse date
            date = parse_date(sys.argv[6])
            todo.eww_progress(75)
            todo.update_task(auth, sys.argv[2], sys.argv[3], sys.argv[4],
                             True, date)
        else:
            todo.eww_progress(75)
            todo.update_task(auth, sys.argv[2], sys.argv[3], sys.argv[4])

        # Set loading state to false in eww and reset variables
        os.system("eww update load_progress=100 loading_form=false "
                  "taskform=false form_type='create' listid='' "
                  "taskid='' listname='' tasktitle='' placeholder='' "
                  "hasduedate=false duedate=false")

    if sys.argv[1] == 'refresh':
        pass

    # Finally, refresh tasklist
    os.system('eww update loading_tasks=true load_progress=15')
    response = todo.get_tasks(auth)

    # Write tasks to file
    todo.eww_progress(90)
    with open(os.path.dirname(__file__)+'/data.json', 'w') as f:
        f.write(json.dumps(response))

    # Refresh JSON
    todo.eww_progress(100)
    subprocess.run(os.path.dirname(__file__)+'/refresh')
    os.system('eww update loading_tasks=false')
