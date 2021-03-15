""" 
    For creating the Session for when we're
    making requests as a bot. 
"""

import json
import pickle
import requests
from bs4 import BeautifulSoup as bs
from urllib.parse import urlparse # for making cache file

# Local Imports
import util
from exceptions import LoginException

MAIN_URL = "http://www.best11.org/"

def make_soup(request):
    """ Given a request object, convert into bs4 object. """
    return bs(request.text, 'lxml')

with open("session_files/user_agent.json") as jf:
    USER_AGENT = json.load(jf)


class Session(requests.Session):
    """ 
    Inherits from the request.Session()
    Adds methods and variables specific to best11. 
    """

    # URLs
    login_suburl = "login.php"

    # File names
    fn_user_details = "session_files/user_details.json"

    # Create session filepath
    # Parse the login_url in order to get netloc data for cache file
    urlData = urlparse(MAIN_URL + login_suburl)

    # Make the filepath for the session file that can be subsequently used.
    fn_session = f"session_files/{urlData.netloc}_session.bat"

    """ 
    This __attrs__ class attribute 
    is called in the requests.Session class by the __getstate__() 
    
    In pickel, the __dict__() method is serialised UNLESS the __getstate__() method
    is called, in which case the return object of __getstate__() will be pickled
    as the contents of the instance.
    In requests.Session, the __getstate__() method returns a list of 
    getattr(x) for x in __attrs__, which is not a real dunder method, but 
    just a list defined within the same request.Session class which contains
    a string list of attributes of the instance.
    When pickeling, this method is called, so that means these items alone
    are pickled. Hence, to ensure variables created in this class are also pickled,
    they must be added to the __attrs__ list.
    """
    __attrs__ = requests.Session.__attrs__
    __attrs__ += ["username", "password", "logged_in", "logged_in_from_cache"]

    @classmethod
    def load_session(cls, session_expire=20):
        file_name = Session.fn_session
    
        # If the file exists and was modified less than <session_expire> minutes ago 
        if util.file_exists(file_name) and util.modified_ago(file_name).in_minutes() <= session_expire:
            print("Attempting to load session...")
            with open(file_name, 'rb') as pf:
                session = pickle.load(pf)
                session.logged_in_from_cache = True
        else:
            print("Attempting to create session...")
            session = Session()
            print("Attempting to login...")
            session()
            session.logged_in_from_cache = False

        return session

    def __init__(self):
        
        # Call session __init__ to reate cookies and other attributes
        super().__init__()

        # Request header for imitating real user
        self.headers.update(USER_AGENT)

        # Called by __repr__
        self.logged_in = False

        self.__get_user_details()

    def __call__(self):
        """
        Call __login_loop() function if not already logged in.
        """
        if self.logged_in:
            print("You're already logged in!")

        self.__login_loop()

    def __repr__(self):
        return f'''{self.__class__.__name__} (\
            \n\tUsername: {self.username}\
            \n\tPassword: {bool(self.password)}\
            \n\tLogged_In: {self.logged_in}\
            \n\t)'''

    def __str__(self):
        return f"{self.__class__.__name__} object (user: {self.username})"

    # --- Overloading ---

    def request(self, method, suburl='', save_cache=True, **kwargs):
        """ 
        ** Overloading **
        Customise request to default to main Best11 url
        And to raise error status if error occurs.
        """
        response = super().request(
            method,
            url=f"{MAIN_URL}{suburl}",
            **kwargs
        )
        
        if not response.ok:
            response.raise_for_status()

        # TODO: this may not be necessary
        if save_cache:
            self.write_session()

        return response

    # --- Saving Session ---

    def write_session(self):
        """ 
        Saves the instance's session to the instance's session file.
        This can subsequently be loaded until the session expires 
        """
        with open(self.fn_session, 'wb') as pf:
            pickle.dump(self, pf)

    # --- Logging In ---

    def __login_loop(self, max_attempts=5):
        """ 
        Keeps attemptng to login until successful
        or reaches max attempts. 
        """
        attempts = 0
        ask_reset = True

        while attempts < max_attempts:
            try:
                self.__login()
            except LoginException:
                if ask_reset:
                    print(f"Could not login with details {self.user_details}")
                    if util.yn("Reset details?"):
                        self.change_user_details()
                    else:
                        ask_reset = False
            else:
                self.logged_in = True
                self.write_session() # Save session to pickle file
                return True

    def __login(self):
        """ 
        Attempt to login to best11.
        Called by the __call__ func for this class.
        """

        print("login url", self.login_suburl)
        print("login details", self.user_details)

        try:
            login_request = self.request(
                "POST",
                suburl = self.login_suburl,
                data = self.user_details
            )
        except:
            # Was unable to make request
            raise LoginException("Unable to login to")

        # Verify logged in by checking redirected URL
        if not self.__valid_login(login_request):
            raise LoginException(f"Incorrect details given: {self.user_details}")
        return True

    def __valid_login(self, request):
        """ 
        Takes the soup resulting from making a post request to log in.
        Checks to see if redirected to club page or bonus page (in either case, meaning that login successful).
        """
        return True if request.url in (f"{MAIN_URL}club.php", f"{MAIN_URL}bonus_zilnic.php") else False

    # --- User details ---

    @property
    def user_details(self):
        """ Returns the username and password as a dict.
        This is useful for logging in. """
        return {'user': self.username, 'pass': self.password}

    def __get_user_details(self):
        """
        (1) Gets user's username and password from json file and returns it.
        If it can't retrieve the information:
        (2) Prompts the user for username and password
        (3) Writes it to the json file
        (4) Goes back to step 1
        """
        file_name = self.fn_user_details

        while True:
            try:
                with open(file_name) as jf:
                    user_details = json.load(jf)
                self.username = user_details['user']
                self.password = user_details['pass']
                return
            except:
                # Get username and password from user input
                print("Please enter your details:")
                username = input("Username: ")
                password = input("Password: ")
                
                if not all([username, password]):
                    print("You entered blank information") 
                    continue
                else:
                    user_details = {'user': username, 'pass': password}
                
                # Write these details to file
                with open(file_name, 'w') as jf:
                    json.dump(user_details, jf)

    def change_user_details(self):
        """ 
        Allows a user to change their details by
        (1) Deleting existing user_details and session data
        (2) Then getting the user_details again.
        """
        # Reset json file
        try:
            with open(self.fn_user_details, 'w'):
                pass
        except FileNotFoundError:
            # File did not need be reset - does not yet exist
            pass

        # Delete session data
        with open(self.fn_session, 'wb') as pf:
            pickle.dump({})
            
        # Call func to get user_details again
        self.__get_user_details()

    # --- Testing ---
    
    def tactics(self):
        """ 
        Returns the user's tactics.
        I use this method to test the program is working/scraping correctly.
        """
        request = self.request("GET", "tactici.php?")
        soup = make_soup(request)

        select = soup.find('select', attrs={'class': 'normal', 'name': 'cpt'})
        options = select.find_all('option')
        [print(option.text) for option in select.find_all('option')]

if __name__ == '__main__':
    session = Session.load_session()