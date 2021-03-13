""" 
    Utility functions.
"""

import pathlib
import pendulum

# Lists with common applications
yes_list = ['y', 'yes', 'yeah', 'confirm']
no_list = ['n', 'no', 'back', 'cancel', 'quit()', 'quit', 'q', 'cls']

# -- User Input --

def yn(inp=None):
    """ While user's response is not in no/yes list, keeps prompting
    if in yes_list -> True
    elif in no_list -> False. """
    pre_string = "y/n:\n> "
    string = f"{inp} {pre_string}" if inp else pre_string
    while True:
        user_response = input(string)
        if user_response in yes_list:
            return True
        elif user_response in no_list:
            return False
        print("Sorry, I didn't understand your response!")

# -- Files --

EPOCH = pendulum.from_timestamp(0)

def file_exists(file_name):
    file_name = pathlib.Path(file_name)
    if not file_name.exists():
        return False
    return True

def last_modified(file_name):
    file_name = pathlib.Path(file_name)
    if not file_name.exists():
        return False
    modified_time = pendulum.from_timestamp(file_name.stat().st_mtime)
    return modified_time

def modified_ago(file_name):
    modified = last_modified(file_name)
    if not modified:
        modified = EPOCH
    now = pendulum.now()
    return now.diff(modified)

# --- Timezones ---

class TimeZones():

    # UTC timezone
    utc = pendulum.timezone('UTC')

    # Server timezone
    server = pendulum.timezone('Europe/Bucharest')

    # Local timezone
    local = pendulum.now().timezone

    @staticmethod
    def to_string(dt, date=True, time=True):
        """ Returns a string in a readable standardised format. """
        if all([date, time]) or not any([date, time]): return dt.format(r"h:mmA ddd Do MMM Y")
        elif date: return dt.format(r"ddd Do MMM Y")
        elif time: return dt.format(r"h:mmA")