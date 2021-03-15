"""
    For grabbing available information about a single club.
"""

# Imports
import re
import pendulum

# Local Imports
from session import make_soup, MAIN_URL
from spider import Best11
import util

class Club(Best11):
    """
    Contains all info pertaining to an individual club
    (e.g. Noworry About MJ), given its id.
    """
    
    def __init__(self, club_id=None, club=None, manager=None):
        """
        Parameters:
            club_id (int > str)
        """
        super().__init__()

        if not any((club_id, club, manager)):
            raise Exception("You must provide either club_id, club or manager")
        elif club_id:
            ## Verify that club_id is num
            if not isinstance(club_id, int):
                # if str number, convert to int
                if not (r"^\d{1,4}$", club_id):
                    raise ValueError("""Please enter the club_id in number form,\
                    or use alternative constructors to initialise using club name or manager.""")
                club_id = int(club_id)
        elif club:
            club_id = self.club_id_from_club(club)
        elif manager:
            club_id = self.club_id_from_manager(manager)        

        self.club_id = club_id
        self.params = {'id': self.club_id}
        self.soup_dict = self.__get_soup_dict()

    def __repr__(self):
        pass

    def __str__(self):
        pass

    # --- Soup ---

    def __get_soup_dict(self):
        """ Returns a dict of multi-use soup elements.
        e.g. the club_info_table is called by multiple properties. """
        request = self.session.request("GET", "vizualizare_club.php?", params=self.params)
        soup = make_soup(request)

        # Set instance var for full soup
        self.soup = soup

        # Common soup elements
        club_info = soup.find_all('table')[3].find_all('tr')[1]
        return {
            'club_info': club_info,
            'club_info_links': club_info.find_all('a'),
            'equipment': soup.find_all('table')[5]
        }
    
    # --- Avatar ---

    @property
    def avatar(self):
        """ Returns the link to a club's avatar. """
        request = self.session.request("GET", "vizualizare_club.php?", params=self.params)
        soup = make_soup(request)

        # Grab avatar link from soup and replace spaces to make working link
        avatar = soup.find_all('table')[1].find_all('tr')[2].find('img').get('src').replace(' ', '%20')

        # If avatar is the defualt img
        if '/standard.jpg' in avatar:
            return False

        full_link = MAIN_URL + avatar
        return full_link

    def download_avatar(self):
        """ Downloads club's avatar to current directory.
        If club's avatar is default, returns False. """

        if not (avatar:= self.avatar):
            return False
        try:
            util.download_file(avatar)
        except:
            raise Exception("Could not download avatar!")

    # --- Main Properties ---

    def __club_is_corrupt(self):
        """ Takes the links on a club's page. Returns True if club is corrupt else False.
        Corrupt means that, for whatever reason, certain elements on the club page are 
        placed slightly differently. So it is useful to know for getting information
        from the page. """
        return True if len(self.soup_dict['club_info_links']) == 3 else False

    @property
    def manager(self):
        """ Returns a club's manager. """
        manager = self.soup_dict['club_info_links'][0].text
        if not manager:
            raise Exception("Could not get manager.")
        return manager

    @property
    def status(self):
        """ Returns a club's status
        | User | Active | Inactive | Corrupt | Bot """
        if self.manager == "BOT Manager": return "bot"
        if self.manager == self.session.username: return "user"
        if self.__club_is_corrupt(): return "corrupt" # NOTE: this order is fine because BOTS don't seem to corrupt
        return "active" if self.club_id in self.active_managers else "inactive"

    @property
    def club_name(self):
        """ Returns a club's name e.g. Noworry About MJ. """
        i = 0 if self.status == "bot" else 1 # location of element changes depending on club status
        return self.soup_dict['club_info'].find_all('font')[i].text

    @property
    def country(self):
        """ Returns the manager's (and therefore club's) nationality. """
        i = 1 if self.status in ('bot', 'user', 'corrupt') else 3
        return self.soup_dict['club_info_links'][i].text

    @property
    def league(self):
        """ Returns the current league of a club. """
        i = 2 if self.status in ('bot', 'user', 'corrupt') else 4
        # Get link that goes to club's current league
        link = self.soup_dict['club_info_links'][i]
        # Get league_id from this link
        league_id = util.get_id_from_href(link.get('href'))
        return league_id

    @property
    def fame(self):
        """ Returns a club's fame. """
        if self.status == "bot": return False
        fame = self.soup_dict['club_info'].find('b').text[:-1]
        return int(fame)

    @property
    def avg_fame_season(self):
        """ Return the average fame accrued each season since a club's origin. """
        if self.status == "bot": return False
        seasons_played = self.current_season - self.origin + 1
        return round(self.fame / seasons_played, 2)

    @property
    def origin(self):
        """ Returns the first season in a club's history - 
        presumably the season a manager started playing. """
        # Make request to club history page
        request = self.session.request("GET", 'istoric_club.php?', params=self.params)
        soup = make_soup(request)
        # Grab last row of table as this will be the earliest season
        original_season = soup.find_all('tr')[-1].find('td').text     
        return int(original_season)   

    @property
    def stadium_capacity(self):
        """ returns a club's stadium capacity if > DEFAULT, which is 10,000
        If it is default, return False. """
        element = self.soup.find_all('table')[8].find('tr').find_all('td')[1].find('b').text
        capacity = int(element.replace('.', ''))
        return 'DEFAULT' if capacity == 10000 else capacity 

    @property
    def team_kit(self):
        soup = self.soup_dict['equipment']
        results = soup.find_all('img', attrs={'src': re.compile("echipament")})
        if len(results) != 2: 
            raise Exception(f"Invalid number for kit: {len(results)}. Should be 2")
        return tuple(i.get('src') for i in results)

    @property
    def sponsors(self):
        soup = self.soup_dict['equipment']
        results = soup.find_all('img', attrs={'src': re.compile("sponsori")})
        if len(results) != 2:
            raise Exception(f"Invalid number of sponsors: {len(results)}. Should be 2")
        return tuple(i.get('src') for i in results)

    @property
    def motto(self):
        # TODO: remove \n\r chars
        """ Returns a club's motto if it has one.
        If the motto is '...', or nothing, return False.
        Note that bot clubs still have a motto so BOT clubs won't break this code. """
        motto = self.soup.find('table').find_all('tr')[1].find('i').text
        if motto == "..." or not motto: 
            return False
        return motto

    # --- Properties Dict ---

    def get_details(self):
        """ Returns club info as dict. """
        return {
            'id': self.club_id,
            'club_name': self.club_name,
            'status': self.status,
            'manager': self.manager,
            'country': self.country,
            'league': self.league,
            'fame': self.fame,
            'origin': self.origin,
            'stadium_capacity': self.stadium_capacity            
        } 

    def print_details(self):
        """ Just a simple function to print 
        the main details of the instance. """
        print()
        for k, v in self.get_details().items():
            print(f"{k}: {v}")


    


if __name__ == "__main__":
    c = Club(200)
