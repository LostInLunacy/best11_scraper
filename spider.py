
import pendulum
import re

# Local imports
from session import make_soup, Session
from exceptions import ArguuemntException
import util
from util import TimeZones as tz      


class Best11():

    # Files
    fn_active_managers = "session_files/active_managers.json"

    # Best11
    player_positions = ('Goalkeeper', 'Defender', 'Midfielder', 'Striker')
    tactic_positions = ('G' 'D', 'M', 'A')

    def __init__(self, session=Session.load_session()):
        
        self.session = session

        # Apply Updates
        self.wealthiest_clubs = self.__get_wealthiest_clubs()
        self.active_managers = self.__get_active_managers()

        self.welcome()

    def welcome(self):
        local_time = tz.to_string(pendulum.now(tz=tz.local))
        server_time = tz.to_string(pendulum.now(tz=tz.server))

        if self.session.logged_in_from_cache:
            print(f"Welcome back, {self.session.username}")
        else:
            print(f"Welcome, {self.session.username}")

        print(f"Local time: {local_time}")
        print(f"Server time: {server_time}")

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

    def get_next_match(self):
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
        return dt

    # -- B11 Utility --
    @staticmethod
    def get_value_from_string(string):
        """ 
        Returns the value in float form given Best11 text 
        e.g. "blah 511.41 C." -> 511.41
        """
        # Pattern to get value
        pattern = r"(-)?(\d{1,2}\.)?(\d{3})(\.\d{2,3})?\s?C?"
        try:
            result = re.findall(pattern, string)[0]
        except IndexError:
            raise IndexError("Could not get value from string")

        # Join all groups ('-', '1.', '244', '.505') -> '-1.244.505'
        result = ''.join(result)

        # If amount >1mil, will have two periods, and thus
        # cannot be converted to float directly. Must first remove
        # first period
        if result.count('.') == 2: result = result.replace('.', '', 1)

        # Get the value
        value = float(result)

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
    

