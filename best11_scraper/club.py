"""
    For grabbing available information pertaining to clubs in the game
"""

import json

# Imports
import re
import pendulum
from collections import Counter

# Local Imports
from session import make_soup
from spider import Best11
import util

from player import Player, UserPlayer

# TODO move all suburls to parent class Spider?

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
            # The club_id has been given. Verify it is num...
            if not isinstance(club_id, int):
                # if str number, convert to int
                if not (r"^\d{1,4}$", club_id):
                    raise ValueError("""Please enter the club_id in number form,\
                    or use alternative constructors to initialise using club name or manager.""")
                club_id = int(club_id)
        elif club:
            # elif passed the club name, get the corresponding club_id for that club
            club_id = self.club_id_from_club(club)
        elif manager:
            # elif passed the club manager, get the corresponding club_id for that manager

            # if set to user, get username from session
            if manager == 'user': manager = self.session.username
            
            club_id = self.club_id_from_manager(manager)        

        self.club_id = club_id
        self.params = {'id': self.club_id}
        self.soup_dict = self.__get_soup_dict()

    def __repr__(self):
        # TODO
        pass

    def __str__(self):
        # TODO
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
        """ Returns the link to a club's avatar.
        r-type: str """
        request = self.session.request("GET", "vizualizare_club.php?", params=self.params)
        soup = make_soup(request)

        # Grab avatar link from soup and replace spaces to make working link
        avatar = soup.find_all('table')[1].find_all('tr')[2].find('img').get('src').replace(' ', '%20')

        # If avatar is the defualt img
        if '/standard.jpg' in avatar:
            return False

        full_link = f"{self.session.MAIN_URL}{avatar}"
        return full_link

    def download_avatar(self):
        """ Downloads club's avatar to current directory.
        If club's avatar is default, returns False. 
        r-type: str """

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
        from the page. 
        r-type: str """
        return True if len(self.soup_dict['club_info_links']) == 3 else False

    @property
    def manager(self):
        """ Returns a club's manager. 
        r-type: str """
        manager = self.soup_dict['club_info_links'][0].text
        if not manager:
            raise Exception("Could not get manager.")
        return manager

    @property
    def status(self):
        """ Returns a club's status
        | User | Active | Inactive | Corrupt | Bot 
        r-type: str """
        if self.manager == "BOT Manager": return "bot"
        if self.manager == self.session.username: return "user"
        if self.__club_is_corrupt(): return "corrupt" # NOTE: this order is fine because BOTS don't seem to corrupt
        return "active" if self.club_id in self.active_club_ids else "inactive"

    @property
    def club_name(self):
        """ Returns a club's name e.g. Noworry About MJ.
        r-type: str """
        i = 0 if self.status == "bot" else 1 # location of element changes depending on club status
        return self.soup_dict['club_info'].find_all('font')[i].text

    @property
    def country(self):
        """ Returns the manager's (and therefore club's) nationality.
        r-type: str """
        i = 1 if self.status in ('bot', 'user', 'corrupt') else 3
        return self.soup_dict['club_info_links'][i].text

    @property
    def league_id(self):
        """ Returns the current league_id of a club.
        r-type: int """
        i = 2 if self.status in ('bot', 'user', 'corrupt') else 4
        # Get link that goes to club's current league
        link = self.soup_dict['club_info_links'][i]
        # Get league_id from this link
        league_id = util.get_id_from_href(link.get('href'))
        return league_id

    @property
    def fame(self):
        """ Returns a club's fame.
        r-type: int """
        if self.status == "bot": return False
        fame = self.soup_dict['club_info'].find('b').text[:-1]
        return int(fame)

    @property
    def avg_fame_season(self):
        """ Return the average fame accrued each season since a club's origin.
        r-type: int """
        if self.status == "bot": return False
        seasons_played = self.current_season - self.origin + 1
        return round(self.fame / seasons_played, 2)

    @property
    def origin(self):
        """ Returns the first season in a club's history - 
        presumably the season a manager started playing.
        r-type: int """
        # Make request to club history page
        request = self.session.request("GET", 'istoric_club.php?', params=self.params)
        soup = make_soup(request)
        # Grab last row of table as this will be the earliest season
        original_season = soup.find_all('tr')[-1].find('td').text     
        return int(original_season)   

    @property
    def stadium_capacity(self):
        """ Returns a club's stadium capacity if > DEFAULT, which is 10,000
        If it is default, return False. 
        r-type: int (or False if == 10,000)"""
        element = self.soup.find_all('table')[8].find('tr').find_all('td')[1].find('b').text
        capacity = int(element.replace('.', ''))
        return 'DEFAULT' if capacity == 10000 else capacity 

    @property
    def team_kit(self):
        """ Returns the images used to make up the club's team kit.
        r-type: tuple """
        soup = self.soup_dict['equipment']
        results = soup.find_all('img', attrs={'src': re.compile("echipament")})
        if len(results) != 2: 
            raise Exception(f"Invalid number for kit: {len(results)}. Should be 2")
        return tuple(i.get('src') for i in results)

    @property
    def sponsors(self):
        """ Returns the names of the club's sponsors 
        r-type: tuple"""
        soup = self.soup_dict['equipment']
        results = soup.find_all('img', attrs={'src': re.compile("sponsori")})

        pattern_to_split_sponsor_link = r"(\w+).gif$"
        sponsors = tuple([x.title() for x in [re.findall(pattern_to_split_sponsor_link, i.get('src')).pop() for i in results]])
        if len(results) != 2:
            raise Exception(f"Invalid number of sponsors: {len(results)}. Should be 2")
        return sponsors
        

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

    @motto.setter
    def motto(self, value):
        """
        Sets the motto for the club tied to the instance.

        To append something to an existing motto, 
        pass the str value 'append: [text to append]'

        r-type: None - just updates via post request
        """
        if value.startswith("append:"):
            _, *value = value.split('append:')[0:]
            value = self.motto + ''.join(value)


        # Edge case
        if (t:= type(value)) is not str:
            raise TypeError(f"Value for objective must be str, not {t}")
        
        # Make request to change motto
        self.session.request(
            'POST',
            'schimba_motto.php',
            data={
                'club': self.club_id,
                'mesaj': value
            }
        )

    @property
    def objective(self):
        """ Returns the club's objective. """
        return self.soup.find_all('table')[12].find_all('tr')[1].find('td').text.strip()

    @objective.setter
    def objective(self, value):
        """ Sets the objective
        1 = Winning
        2 = Top 3
        3 = Top half
        4 = Mid position
        5 = Avoiding relegation
        """
        # Edge case
        if (t:= type(value)) is not int:
            raise TypeError(f"Value for objective must be int, not {t}")
        elif value not in range(1,6):
            raise Exception(f"Value out of inclusive range 1-5: {t}")

        # Make request to change objective
        self.session.request(
            'POST',
            'schimba_obiectiv.php',
            data = {
                'club': self.club_id,
                'obiectiv': value
            }
        )
        

    @property
    def wealth_rank(self):
        """
        Returns the club's position within the wealth_100
        r-type: int (or False if outside wealth_100)
        """
        for rank, club_id in self.wealth_100.items():
            if self.club_id == club_id:
                return int(rank)
        return False

    # --- Properties Dict ---

    def get_details(self):
        """ Returns club info as dict. """
        return {
            'id': self.club_id,
            'club_name': self.club_name,
            'status': self.status,
            'manager': self.manager,
            'country': self.country,
            'league_id': self.league_id,
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

    # --- Club Players ---

    def __get_player_ids_from_squad_table(self, table):
        """ Returns list of player_ids from a given table in squad table soup.
        e.g. returns all goalkeepers, or returns all defenders """

        """ Grabs the player profile link for each player on the squad page,
        NOTE that there are two different ways of viewing a squad. When you
        look at your own club, you have access to more information. However
        you can only do this for your own club. This function makes use of the 
        more restricted view, which is how you look at others' clubs. """
        player_hrefs = [n.find('td').find_all('a')[-1].get('href') for n in table.find_all('tr')[1:]]

        # Grab and return id from each href in the above list
        return [util.get_id_from_href(x) for x in player_hrefs]

    @property 
    def player_dict(self):
        """ Returns a dict of players within that team by position. """
        request = self.session.request("GET", 'vizualizare_jucatori.php?', params=self.params)
        tables = make_soup(request).find_all('table')
        positions = self.player_positions # (Goalkeeper, Defen...)

        # NOTE: needs a comment here
        player_dict = {}
        iterated_through = 1
        for position in positions:
            player_ids_for_position = self.__get_player_ids_from_squad_table(tables[iterated_through])
            iterated_through += len(player_ids_for_position) + 2 
            player_dict[position] = player_ids_for_position
        return player_dict

    @property
    def players_in_each_position(self):
        """ Return tuple of total number of players in that position. """
        positions = self.player_positions # Goalkeeper, Defen...
        return tuple([len(self.player_dict[p]) for p in positions])

    @property
    def player_ids(self):
        """ Returns concatenated list of all player_ids. """
        return util.flat_list(self.player_dict.values())

    # --- Messaging ---

    @property
    def msg_id(self):
        """ Returns the ID needed to message the manager. """
        if self.status == "bot":
            raise Exception("Tried to get msg_id of bot club.")
        elif self.status == "user":
            """ When you send a message on this game either via Guestbook or Direct Message,
            you are using your message_id. Hence, when sending a message to your own guestbook,
            you're essentially messaging yourself. Since a user cannot Direct Message themselves via
            the send message button like they can with other users,
            this is the only way to grab this information, without navigating to the create message page,
            iterating through the ids to send to and breaking at the name of the user (you can
            send a message to yourself using your own id), which obviously takes much longer. """
            input_tag = self.soup.find('input', attrs={'name': 'user'})
            msg_id = int(input_tag.get('value'))
        else:
            msg_href = self.soup_dict['club_info'].find_all('a')[1].get('href')
            msg_id = int(re.findall(r"catre=(\d{1,8})", msg_href)[0])
        return msg_id

    # --- Transfer ---

    @staticmethod
    def __get_date_from_transfer(string):
        """ Returns the date given a string containing the transfer. """
        return util.regex_between(string, r"popup\('", r"\d\d:")

    @staticmethod
    def __get_other_club_from_transfer(string):
        """ Returns other club involved in the transfer given a string containing said transfer """
        return util.regex_between(string, r"b&gt;", r"&lt;")

    def __get_individual_transfer_info(self, transfer):
        """ Get the information for an individual transfer on club's transfers page. """
        try:
            amount = self.get_value_from_string(transfer.find('b').text) # Get transfer amount
        except:
            print(f"Could not get transfer info for transfer {transfer.find('b').text}")

        td = transfer.find('td')
        player_name = td.text # that's player, not manager
        player_id = util.get_id_from_href(td.find_all('a')[1].get('href'))


        text_info = str(td)
        date = self.__get_date_from_transfer(text_info) # Get date of transfer           
        other_club = self.__get_other_club_from_transfer(text_info) # Other club involved in transfer

        # Return dict containing all info
        return {
            'amount': amount,
            'date': date,
            'other_club': other_club,
            'player_id': player_id,
            'player_name': player_name
        }

    @property
    def transfers(self):
        """
        Returns a list of transfers (bought and sold), sorted by date
        r-type: list of dicts
        """
        request = self.session.request("GET", "transferuri_club.php?", params=self.params)
        soup = make_soup(request)

        # For i in View all Transfers > rows of data under transfers(in) and transfers(out)
        # grab information about each transfer through the __get_individual_transfer_info() func
        bought = [self.__get_individual_transfer_info(i) for i in soup.find_all('table')[2].find_all('tr')]
        sold = [self.__get_individual_transfer_info(i) for i in soup.find_all('table')[4].find_all('tr')]

        [x.update({'type': 'sell'}) for x in sold]
        [x.update({'type': 'buy'}) for x in bought]

        transfers = sorted(list(bought + sold), key=lambda k: pendulum.from_format(k['date'], 'YYYY-MM-DD'))
        return transfers

    @property
    def transfers_bought(self):
        """ Returns the transfers involving players the club has bought. 
        r-type: list of dicts """
        return [i for i in self.transfers if i['type'] == 'buy']

    @property
    def transfers_sold(self):
        """ Returns the transfers involving players the club has sold.
        r-type: list of dicts. """
        return [i for i in self.transfers if i['type'] == 'sell']

    @property
    def transfers_sold_to_bank(self):
        """ Returns the transfers involving players the club has sold to the bank.
        r-type: list of dicts. """
        return [i for i in self.transfers_sold if i['other_club'] == "Bank"]

    @property
    def transfers_sold_to_club(self):
        """ Returns the transfers involving players the club has sold to the other clubs.
        r-type: list of dicts. """
        return [i for i in self.transfers_sold if i['other_club'] != "Bank"]

    @property
    def home_player_ids(self):
        """
        NOTE: This will miss players who retired as a result of turning 36
        These cannot be scraped; the data is not retrievable.
        """

        ## Get home players the club has transferred
        transfers = self.transfers
        unique_players = set([i['player_id'] for i in transfers])
        home_players = []

        for transfer in transfers:
            if (player_id := transfer['player_id']) not in unique_players:
                continue
            if transfer['type'] == 'sell':
                home_players.append(player_id)
            unique_players.remove(player_id)
        
        ## Get home players currently at the club
        current_players = self.player_ids
        bought_players = set([i['player_id'] for i in self.transfers_bought])
        
        for player_id in current_players:
            if player_id in bought_players:
                continue
            home_players.append(player_id)

        ## Sort the player_ids such that most recent players are last in the list
        return sorted(home_players)

    def get_home_player_ids(self, recent=0):
        if not recent: return self.home_player_ids
        
        try:
            return self.home_player_ids[:-recent-1:-1]
        except IndexError:
            # Out of range - recent > len(home_player_ids)
            # So just return the full list
            return self.home_player_ids

    def get_talent_luck(self, recent=0):
        """
        NOTE: this property takes a long time to execute!
        """
        player_ids = self.get_home_player_ids(recent)

        try:
            result = dict(sorted(Counter([f"{Player(i).talent}*" for i in player_ids]).items()))
        except:
            # Occasional error whereby one or more player_ids cannot be found.
            # In this case, the player is skipped in a standard for loop, since the info can't be retrieved.
            player_talents = []
            for player_id in player_ids:
                try:
                    player = Player(player_id)
                    player_talents.append(f"{player.talent}*")
                except:
                    pass
            result = dict(sorted(Counter(player_talents).items()))
        finally:
            return result
            
    # --- Objects ---
    @property  
    def player_objects(self):
        """ Returns a player object for each player owned by the club. """
        pass
        return [Player(p) for p in self.player_ids]


class UserClub(Club):

    def __init__(self):
        
        # Get the user's club_id
        club_id = Best11().get_user_club_id()

        # Initialise a Club object with user's club_id
        super().__init__(club_id)
                
    @property
    def tables(self):
        """
        Returns the soup for the club.php which contains
        extra info about the user's club.

        NOTE: I turned this from method used in __init__ to property
        so that it remains constantly updated
        """
        response = self.session.request("GET", "club.php?")
        tables = make_soup(response).find_all('table')
        return tables

    @property
    def cash_balance(self):
        """ Returns the user's cash_balance. r-type: int. """
        value = self.tables[20].find_all('td')[1].text
        return self.get_value_from_string(value)

    @property
    def tp_balance(self):
        """ Returns the user's tp_balance. r-type: int. """
        value = self.tables[22].find_all('td')[1].text
        return self.get_value_from_string(value)

    @property
    def fans(self):
        """ Returns the number of fans you have. r-type: int """
        value = self.tables[10].find('b').text
        return int(value)

    @property
    def fans_mood(self):
        """ Returns the mood of your ciub's fans. r-type: int. """
        text = self.tables[10].find('a').get('onmouseover')
        value = re.findall(r"\d{1,3}%", text)[0][:-1] # [:-1] gets rid of the %
        return int(value)
        
    @property
    def pitch_quality(self):
        """ Returns the condition of your pitch out of 100. r-type: int. """
        value = self.tables[8].find_all('b')[-1].text[:-1]
        return int(value)

    @property
    def player_objs(self):
        """ 
        Returns a player object for each player owned by the club. r-type: list
        NOTE: overrides parent method.
        """
        return [UserPlayer(p) for p in self.player_ids]


if __name__ == "__main__":
    pass

    # from tqdm import tqdm

    # # club = Club(club="Noworry About MJ")
    # # print(type(club.origin))

    # club = Club(manager="user")
    # home_players = club.get_home_player_ids()

    # home_player_objs = sorted([Player(p) for p in tqdm(home_players)], key=lambda x:x.skill_total, reverse=True)

    # for i, player in enumerate(home_player_objs):
    #     print(f"{i+1:3d} {player.player_name} [{player.player_id}]: {player.skill_total}")
