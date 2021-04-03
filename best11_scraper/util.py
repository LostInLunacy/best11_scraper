""" 
    Utility functions.
"""

import json
import re
import pathlib
import pendulum
import requests
import shutil
import os

# The main path of the directory
def get_working_directory():
    os.chdir("..")
    return os.path.abspath(os.curdir)

MAIN_DIRECTORY = get_working_directory()
SESSION_FILES = os.path.join(MAIN_DIRECTORY, "session_files")

def combine_path(*paths):
    return os.path.join(*paths)

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

def get_last_modified(file_name):
    file_name = pathlib.Path(file_name)
    if not file_name.exists():
        return False
    modified_time = pendulum.from_timestamp(file_name.stat().st_mtime)
    return modified_time

def get_modified_ago(file_name):
    modified = get_last_modified(file_name)
    if not modified:
        modified = EPOCH
    now = pendulum.now()
    return now.diff(modified)

def apply_update_timeago(file_name, func, **time_ago):
    """
    Updates a json file
    """
    if not time_ago:
        raise Exception("No arguments given for time_ago!")

    time_ago = pendulum.duration(**time_ago)

    if get_modified_ago(file_name) > time_ago:
        result = func()
        with open(file_name, "w") as jf:
            json.dump(result, jf)
            

def apply_update_timeofday(file_name, func, **time_of_day):
    """
    Parameters:
    - func (function) - to be executed if file needs updating.
    The result will then be written to the given file.
    """
    if not time_of_day:
        raise Exception("No arguments given for time_ago!")
    time_of_day = pendulum.duration(**time_of_day)
    if time_of_day > pendulum.duration(days=1):
        raise Exception("Time must be shorter than one day!")

    now = pendulum.now(tz=TimeZones.server)
    modified = get_last_modified(file_name)

    need_update = False

    if now.diff(modified).in_days > 1:
        return

    """
    Scenarios that would require an update of the json file
    Updated today:
    - It is now after target time, file was updated before
    Updated yesterday:
    - It is now before target time, file was updated before
    - It is now after target time, file was updated after
    """
    if now.date() == modified.date():
        if now.time() > time_of_day and modified.time() < time_of_day:
            need_update = True
    elif now.yesterday().date() == modified.date():
        if now.time() < time_of_day and modified.time() > time_of_day:
            need_update = True
        elif now.time() > time_of_day and modified.time() > time_of_day:
            need_update = True

    if not need_update:
        return

    result = func()
    with open(file_name, "w") as jf:
        json.dump(result, jf)
        



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

# -- Regex --

def get_id_from_href(href):
    """ Extracts and returns int(id) from the a Best11 href using regex.
    rtype: int """
    matches = re.findall(r"id=(\d{1,8})", href)
    try: 
        return int(matches.pop(0))
    except: 
        raise Exception("Could not get href.")

def regex_between(string, before, after):
    """ Returns the text between two strings using regex. 
    Takes the strign to search, and before and after strings. """
    if(any([type(x) is not str for x in (string, before, after)])):
        raise TypeError("string, before and after vars must all be of type str")
    pattern = before + r'(.*?)' + after
    return re.search(pattern, string).group(1).strip()

# -- Collections --

def flat_list(list_of_lists):
    """ Merges a list of lists into a single list. """
    return [item for sublist in list_of_lists for item in sublist]

def flat_list_of_dicts(list_of_dicts):
    """ Merges a list of dicts into a single dict. """
    keys = flat_list([i.keys() for i in list_of_dicts])
    if len(set(keys)) != len(keys):
        raise Exception("Non-unique keys - cannot merge list of dicts!")

    d = list_of_dicts.pop()
    while list_of_dicts:
        d.update(list_of_dicts.pop())
    return d

def dict_percentage(d):
    s = sum(d.values())
    result = {k:v/s*100 for k, v in d.items()}
    return result

# --- Downloading ---

def download_file(url):
    """ Download an individual file given a url. """
    file_name = url.split('/')[-1]
    with requests.get(url, stream=True) as r:
        with open(file_name, 'wb') as file:
            shutil.copyfileobj(r.raw, file)

if __name__ == "__main__":
    pass
