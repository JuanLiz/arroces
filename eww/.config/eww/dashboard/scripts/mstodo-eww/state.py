#!/bin/python

import json
import os
import sys

# Control if a list is dropped down
with open(os.path.dirname(__file__)+'/data.json', 'r') as f:

    props = json.loads(f.read())

    # Change values in JSON
    for list in props:
        if list["id"] == sys.argv[1] and not list["dropped"]:
            list["dropped"] = True
            list["height"] = list["fallback_height"]
            list["icon"] = ""
        elif list["id"] == sys.argv[1] and list["dropped"]:
            list["dropped"] = False
            list["height"] = 0
            list["icon"] = ""

# Write file again
with open(os.path.dirname(__file__)+'/data.json', 'w') as ff:
    ff.write(json.dumps(props))
