#!/bin/python

import atexit
import datetime as dt
import json
import os
import sys

import msal
import requests

endpoint = "https://graph.microsoft.com/v1.0/me/todo/lists/"
authority = "https://login.microsoftonline.com/common"
scope = ["Tasks.ReadWrite"]


def initialize_auth(client_id):
    '''
    Initialize authentication. Creates or reads existing
    cache and initialize app instance
    '''

    # Store token in cache
    cache = msal.SerializableTokenCache()
    if os.path.exists(os.path.dirname(__file__)+"/my_cache.bin"):
        cache.deserialize(open(os.path.dirname(
            __file__)+"/my_cache.bin", "r").read())

    atexit.register(
        lambda: open(os.path.dirname(__file__)+"/my_cache.bin",
                     "w").write(cache.serialize())
        # Hint: The following optional line persists only when state changed
        if cache.has_state_changed else None
    )

    # Create a preferably long-lived app instance which maintains a token cache
    app = msal.PublicClientApplication(
        client_id, authority=authority,
        token_cache=cache
    )

    return app


def authenticate(app):
    '''
    Authenticate with device authentication flow
    '''
    flow = app.initiate_device_flow(scopes=scope)
    if "user_code" not in flow:
        raise ValueError(
            "Fail to create device flow. Err: %s" % json.dumps(flow, indent=4))
    print(flow["message"])
    sys.stdout.flush()  # Some terminal needs to ensure the message is shown
    result = app.acquire_token_by_device_flow(
        flow)  # By default it will block

    if "access_token" in result:
        return result
    else:
        print(result.get("error"))
        print(result.get("error_description"))
        # You may need this when reporting a bug
        print(result.get("correlation_id"))


def get_token_from_cache(app):
    '''
    Try to get token from cache
    '''
    # The pattern to acquire a token looks like this.
    result = None

    # We now check the cache to see if we have some end users signed in before.
    accounts = app.get_accounts()
    if accounts:
        # Now let's try to find a token in cache for this account
        result = app.acquire_token_silent(scope, account=accounts[0])

    # If none is returned, you need to authenticate first with device code flow
    return result


def eww_progress(value):
    '''
    Update eww circular progress
    '''
    os.system('eww update load_progress='+str(value))


def get_tasks(auth):
    '''
    Get unfinished tasks
    '''

    progress = 30
    response = []

    # Get To Do task lists
    tasklists = requests.get(  # Use token to call downstream service
        endpoint,
        headers={'Authorization': 'Bearer ' + auth['access_token']},).json()
    eww_progress(progress)
    # Get uncompleted tasks from list
    for list in tasklists["value"]:
        tasks = requests.get(
            endpoint+list["id"]+'/tasks/?$filter=status eq \'notStarted\'',
            headers={'Authorization': 'Bearer ' + auth['access_token']}).json()

        finaltasks = []
        for task in tasks["value"]:

            # Parse date
            if "dueDateTime" in task:
                task["hasDueDate"] = True
                datetime = task["dueDateTime"]["dateTime"]

                # Check current time for define time color
                date = dt.datetime.strptime(
                    datetime, "%Y-%m-%dT%H:%M:%S.0000000")
                # Assign red color if task is overdue
                if date < dt.datetime.now():
                    datecolor = "#BF3768"
                else:
                    datecolor = "#96E072"

                # Format date as short month and day (Jan. 15)
                task["dueDateTime"]["dateTime"] = date.strftime("%b. %d")

            # Set default values if task don't have due date to avoid errors
            else:
                date = dt.datetime.now()
                datecolor = "#BF3768"
                task["hasDueDate"] = False
                task.setdefault(
                    "dueDateTime", {"dateTime": None, "timeZone": None},
                )

            # Write to tasks array
            finaltasks.append({'id': task["id"], 'title': task["title"],
                               'hasDueDate': task["hasDueDate"],
                               'shortduedate': task["dueDateTime"]["dateTime"],
                               'duedate': [date.day, date.month, date.year],
                               'datecolor': datecolor}
                              )
            # Update circular progress
            progress += 2
            eww_progress(progress)

        # Calculate size for widget height.
        if len(finaltasks) >= 10:
            height = 375
        else:
            # Each task has ~64 of height
            height = len(finaltasks)*64

        # Write response, with lists and tasks
        response.append({'id': list["id"], 'name': list["displayName"].upper(),
                        'count': len(finaltasks), 'height': 0,
                         'fallback_height': height, 'dropped': False,
                         'icon': "", 'tasks': finaltasks}
                        )
        # Update circular progress
        progress += 5
        eww_progress(progress)

    return response


def create_task(auth, list_id, title, hasduedate=False, duedate=None):
    '''
    Create a To Do task
    '''
    params = {'title': title, 'status': 'notStarted'}

    # Add due date if specified
    if hasduedate:
        params['dueDateTime'] = {'dateTime': duedate, 'timeZone': 'UTC'}

    # Send POST request to API for create task
    request = requests.post(endpoint+list_id+'/tasks/',
                            headers={'Authorization': 'Bearer ' +
                                     auth['access_token'],
                                     "Content-Type": "application/json"},
                            json=params)

    if not request.status_code == 201:
        print('Code '+str(request.status_code)+': '+request.reason)


def complete_task(auth, list_id, task_id):
    '''
    Set 'status' task to completed
    '''
    # Send PATCH request to API for complete task
    request = requests.patch(endpoint+list_id+'/tasks/'+task_id,
                             headers={'Authorization': 'Bearer ' +
                                      auth['access_token'],
                                      "Content-Type": "application/json"},
                             json={'status': 'completed'}
                             )
    if not request.status_code == 200:
        print('Code '+str(request.status_code)+': '+request.reason)


def update_task(auth, list_id, task_id, title, hasduedate=False, duedate=None):
    '''
    Update task details
    '''
    params = {'title': title, 'status': 'notStarted'}

    # Update due date if specified
    if hasduedate:
        params['dueDateTime'] = {'dateTime': duedate, 'timeZone': 'UTC'}
    # Otherwise, delete due date
    else:
        params['dueDateTime'] = None

    # Send PATCH request to API for update task
    request = requests.patch(endpoint+list_id+'/tasks/'+task_id,
                             headers={'Authorization': 'Bearer ' +
                                      auth['access_token'],
                                      "Content-Type": "application/json"},
                             json=params)

    if not request.status_code == 200:
        print('Code '+str(request.status_code)+': '+request.reason)
