""" 
    - Welcoming the user (of the program)
    - General functions and variables relating to Best11
        - e.g. for reading data on wealth_100, active_managers
        - getting current season, week etc.
"""

import pendulum
import re
import json

# Local imports
from session import make_soup, Session
from exceptions import ArguuemntException
import util
from util import TimeZones as tz

class Best11():

    # Files
    fn_active_managers = "session_files/active_managers.json"
    fn_wealth_100 = "session_files/wealth_100.json"
    fn_next_match = "session_files/next_match.json"

    # Names of player positions within the game
    player_positions = ('Goalkeeper', 'Defender', 'Midfielder', 'Striker')

    # For making requests to change tactics
    tactic_positions = ('G' 'D', 'M', 'A')

    def __init__(self, session=Session.load_session()):
        
        self.session = session

        # Apply updates to files
        util.apply_update_timeago(self.fn_active_managers, self.__get_active_managers, days=1)
        util.apply_update_timeago(self.fn_wealth_100, self.__get_wealthiest_clubs, minutes=30)            

    def welcome(self):
        local_time = tz.to_string(pendulum.now(tz=tz.local))
        server_time = tz.to_string(pendulum.now(tz=tz.server))
        print(f"Welcome, {self.session.username}")
        print(f"Local time: {local_time}")
        print(f"Server time: {server_time}")

    @property
    def current_season(self):
        """ Returns the current season in best11. 
        r-type: int """
        return self.get_season_week()[0]

    @property
    def current_week(self):
        """ Returns the current week in best11.
        r-type: int """
        return self.get_season_week()[1]

    @property
    def active_managers(self):
        """ Returns the corresponding club_id for every active manager in the game
        r-type: list. """
        with open(self.fn_active_managers) as jf:
            active_managers = json.load(jf)
        return active_managers

    @property
    def wealth_100(self):
        with open(self.fn_wealth_100) as jf:
            wealth_100 = json.load(jf)
        return wealth_100

    def get_season_week(self):
        """ 
        Returns the current season and week of play
        r-type: tuple
        r-format: (season, week); (int, int)
        """

        # Make request to league page. 
        # ID has to be number, but number itself does not matter. We only need season
        request = self.session.request("GET", suburl="campionat.php?", params={'id': 1})
        soup = make_soup(request)

        # Get season
        pattern = r"Season : « (\d{1,3}) »"
        season = int(re.findall(pattern, soup.find('td').text)[0])

        # Get week
        week = int(soup.find_all('table')[1].find_all('tr')[1].find_all('td')[2].text)
        return season, week

    def __get_wealthiest_clubs(self):
        """
        Returns a dictionary of the richest 100 Best11 clubs.
        r-type: dict
        r-format {wealth_rank: club_id}; {int: int}
        """
        
        request = self.session.request(
            "GET",
            suburl = "wealth.php"
        )

        soup = make_soup(request)
        table_rows = soup.find('table').find_all('tr')[1:]

        table_entries = [{int(i.find_all('td')[0].text): util.get_id_from_href(i.find_all('td')[2].find('a').get('href'))} for i in table_rows]
        wealth_100 = util.flat_list_of_dicts(table_entries)
        return wealth_100

    def __load_active_managers(self):
        """ Loads an existing list of active managers from file. """
        file_name = self.fn_active_managers
        if util.get_modified_ago(file_name).days < 7:
            with open(file_name) as jf:
                active_managers = json.load(jf)
            return active_managers
        return False          

    def __get_active_managers(self):
        """
        Returns a list of active managers
        r-type: list
        r-format: [club_ids...]; [int]
        """        
        # Make post request via Community > Users > Search > Search by manager
        request = self.session.request(
            "POST",
            "useri.php?",
            params = {'pag': 'cauta'},
            data = {'cautare': 2, 'manager': ''} # Leave manager blank - shows all
        )
        soup = make_soup(request)

        # Grab the table containing table rows, which each contain data for...
        # User, Action, Club, Last Login
        table = soup.find_all('table')[2]

        # Manager considered inactive if last_logged_in before target_dt
        server_time = pendulum.now(tz=tz.server)
        target_dt = server_time.subtract(days=7)

        def is_active(tr):
            """
            Returns the club_id of the club if they are active
            Else returns False
            """
            # Get last logged in
            last_logged_in = tr.find_all('td')[3].text

            # Bypass weird Best11 error wherby the year is 0 
            # NOTE These managers are no longer active regardless.
            year = int(last_logged_in.split('-')[0])
            if year == 0:
                return False
            
            # Convert to pendulum.datetime
            last_logged_in = pendulum.parse(last_logged_in, tz=tz.server)
            if last_logged_in < target_dt:
                # Manager is inactive
                return False

            # Manager is active
            href = tr.find_all('td')[2].find('a').get('href')
            club_id = util.get_id_from_href(href)
            return club_id

        # Get all table rows in users search query soup
        table_rows = table.find_all('tr')[1:]

        # Run is_active() func for each manager
        active_managers = []
        while table_rows:
            # Add each manager to the list if they are active
            if n:= (is_active(table_rows.pop())):
                active_managers.append(n)
        return active_managers

    def get_next_match(self, string=True):
        """
        Goes to the schedule page
        Grabs the dat of the first match that has '-' for its result (i.e. has not yet been played)
        """
        # Make request to schedule page
        request = self.session.request("GET", "meciuri.php")
        soup = make_soup(request)

        # Table containing matches
        table = soup.find_all('table')[1]
        # Find td containing first instance of match with '-' in result column
        td = table.find('td', text=re.compile(r'^-$'))
        # Get the parent table_row which contains the date
        tr = td.parent
        # Get the date
        date = tr.find('td').text

        # Convert to dt object
        dt = pendulum.from_format(date, "YYYY-MM-DD", tz=tz.server).set(hour=17, minute=45)
        # Set hour to match_start time
        if string: dt = dt.format('dddd Do [of] MMMM h:mm A')
        return dt

    # -- Getting club_id --
    def get_user_club_id(self):
        """ Returns the club_id for the user.
        r-type: int """
        return self.club_id_from_manager(self.session.username)

    def club_id_from_club(self, club):
        """
        Given a club name, returns the club's id
        r-type: int

        Parameters:
            - club (str) - case doesn't matter
        """

        club = club.lower() # Ensure lowercase club parameter
        request = self.session.request(
            "POST",
            suburl="useri.php?",
            params = {'pag': 'cauta'},
            data = {'cautare': 3, 'denumire_club': club}
        )
        soup = make_soup(request)
        table_rows = soup.find_all('table')[2].find_all('tr')[1:]

        get_href = lambda index: table_rows[index].find_all('td')[2].find('a').get('href')
        get_result = lambda index: table_rows[index].find_all('td')[2].find('a').text
        
        index = 0
        while index < len(table_rows):
            try:
                search_result = get_result(index)
            except:
                return False 

            # Verifies that (team_name == club) where club is what you're searching for
            if search_result.lower() == club:
                href = get_href(index)
                club_id = util.get_id_from_href(href)
                return club_id
            else:
                pass
            index += 1
        return False

    def club_id_from_manager(self, manager):
        """
        Given a manager's name, returns their club's id
        r-type: int

        Parameters:
            - manager (str) - case doesn't matter
        """

        manager = manager.lower() # Ensure lowercase club parameter
        request = self.session.request(
            "POST",
            suburl="useri.php?",
            params = {'pag': 'cauta'},
            data = {'cautare': 2, 'manager': manager}
        )
        soup = make_soup(request)
        table_rows = soup.find_all('table')[2].find_all('tr')[1:]

        get_href = lambda index: table_rows[index].find_all('td')[2].find('a').get('href')
        get_result = lambda index: table_rows[index].find_all('td')[0].find('b').text

        index = 0
        while index < len(table_rows):
            try:
                search_result = get_result(index)
            except:
                return False 

            # Verifies that (team_name == manager) where manager is what you're searching for
            if search_result.lower() == manager:
                href = get_href(index)
                club_id = util.get_id_from_href(href)
                return club_id
            else:
                pass
            index += 1
        return False

    # -- B11 Utility --
    @staticmethod
    def get_value_from_string(string):
        """ 
        Returns the value in float form given Best11 text 
        e.g. "blah 511.41 C." -> 511.41
        """
        # Pattern to get value
        pattern = r"(-)?(\d{1,2}\.)?(\d{1,3})(\.\d{2,3})?\s?(?:C|TP)?"
        try:
            result = re.findall(pattern, string)[0]
        except IndexError:
            if "0 C" in string:
                return 0
            raise IndexError("Could not get value from string")

        # Join all groups ('-', '1.', '244', '.505') -> '-1.244.505'
        result = ''.join(result)

        # If amount >1mil, will have two periods, and thus
        # cannot be converted to float directly. Must first remove
        # first period
        if result.count('.') == 2: result = result.replace('.', '', 1)

        under1k = False
        if result.count('.') == 0: under1k = True

        # Get the value
        value = float(result)

        if under1k: value /= 1000

        # If value after decimal point is zero, convert to int.
        return int(value) if int(value) == value else value

    # -- Debugging --
    @staticmethod
    def soup_by_numbers(find_all_soup_object):
        """ For i in find_all_soup_object, prints the type and number. 
        Allows for easy searching of HTML that doesn't have unique identifiers. """
        for x, element in enumerate(find_all_soup_object):
            print(f"\n\n{element.name.upper()} {x}\n{element.prettify()}")



if __name__ == "__main__":

    best11 = Best11()
    

