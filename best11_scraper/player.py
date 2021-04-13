"""
    For grabbing available information pertaining to players
    By player I mean e.g. Meg Myers [ID: 234841], not a real player of the game
    Though you can also get the club's manager
"""

import re
import json
from statistics import mean

# Local imports
from session import make_soup
from spider import Best11
from session import make_soup
import util

# Bug fixing
from time import sleep
from tqdm import tqdm

class Search(Best11):

    suburl_search_menu = 'cauta_jucatori.php'
    suburl_search_result = 'lista_jucatori.php'

    def __init__(
        self,
        position, # Goalkeeper, Defender, Midfielder, Striker
        nationality=None,
        age_category=0,
        skills=(10,10,10),
        exp=0,
        fixed=(1,1,1,5,5)
    ):
        super().__init__()

        # -- Data validation --
        assert isinstance(age_category, int) and age_category in range(0,5)
        assert isinstance(skills, tuple) and len(skills) == 3 and [i in range(10,100) for i in fixed]
        assert isinstance(fixed, tuple) and len(fixed) == 5 and [i in range(1,6) for i in fixed]
        assert isinstance(exp, int) and exp in range(0,501)
        self.__validate_position(position)
        # Set the corresponding ids for each nationality and check passed nationality is valid
        self.nationality_ids = self.__get_nationality_ids()
        self.__validate_nationality(nationality)

        # -- Set instance variables --
        self.age_category = age_category
        self.skills = skills
        self.fixed = fixed
        self.exp = exp

        self.results_table = self.__get_results_table()

    def __get_results_table(self):

        # Data for post request
        data = {
            'tara': self.nationality,
            'varsta': self.age_category,
            'pozitie': self.position,
            'A1': self.skills[0],
            'A2': self.skills[1],
            'A3': self.skills[2],
            'EXP': self.exp,
            'AMB': self.fixed[0],
            'INT': self.fixed[1],
            'REZ': self.fixed[2],
            'AGR': self.fixed[3],
            'VUL': self.fixed[4]
        }

        # Conduct the search
        search_result = self.session.request(
            'POST',
            suburl=self.suburl_search_result,
            data=data
        )

        soup = make_soup(search_result)

        try:
            results_table = soup.find_all('table')[1]
        except:
            if soup.find('font', attrs={'color': 'red'}).text.startswith("No player was found"):
                # No players were found
                return []
            else:
                raise

        return results_table

    def get_avg_stats(self, specific_age=None, active_teams_only=True):
        """
        # TODO computes the average stats for players owned by active teams.
        """
        # -- Get data from search --
        results_table = self.results_table
        if not results_table:
            return False
        top_row_data = [i.find_all('td') for i in results_table.find_all('tr')[1::2]]

        # -- Refine by specfic age
        def equals_specific_age(entry):
            return int(entry[1].text) == specific_age
        if specific_age:
            top_row_data = [i for i in top_row_data if equals_specific_age(i)]

        # -- Refine by active teams
        def has_active_team(entry):
            return entry[0].find('b').text in active_clubs

        if active_teams_only:
            active_clubs = [i['club'] for i in self.active_managers]
            top_row_data = [i for i in top_row_data if has_active_team(i)]

        avg_stats = [sum([float(j.text) for j in i[2:5]]) for i in top_row_data]
        return round(mean(avg_stats))

    def __call__(self):
        results_table = self.results_table

        player_id_pattern = r"vizualizare_jucator.php\?id=(\d+)$"
        player_links = [i.get('href') for i in results_table.find_all('a', attrs={'href': re.compile(player_id_pattern)})]
        player_ids = [re.findall(player_id_pattern, link)[0] for link in player_links]
        return player_ids

    """
    ** __init__ related methods **
    """
    def __get_nationality_ids(self):
        """
        Return a list of nationality_ids or conducting the search
        e.g. Albania = 1, Argentina = 2...

        r-type: list
        """
        response = self.session.request(
            'GET',
            suburl=self.suburl_search_menu,
        )

        soup = make_soup(response)
        country_select = soup.find('select', attrs={'name': 'tara'})

        # Cannot use index to convert nationality to nationality_id
        # Because redboy has removed some ids or something
        # Whatever the reason, some numbers are skipped, so it wouldn't work

        # Instead I used a dict comprehension
        options = {i.text.lower(): int(i.get('value')) for i in country_select.find_all('option')[1:]}
        return options  

    def __validate_position(self, position):
        """ Check that the position is valid.
        If it is: set the instance variable """
        try:
            self.position = self.player_positions.index(position)+1
        except IndexError:
            raise ValueError(f"Unknown position: {position}\nMust be in {self.player_positions}")

    def __validate_nationality(self, nationality):
        """ Check that the nationality is valid.
        If it is: set the instance variable """
        if nationality:
            try:
                nationality = self.nationality_ids[nationality.lower()]
            except IndexError:
                raise ValueError(f"Unknown nationality: {nationality}")
        self.nationality = nationality


class Player(Best11):
    """ Contains all info pertaining to an individual player (e.g. Leyers Carletto [ID: 302424]),
    given their id. """

    # Files
    fn_peer_averages = "session_files/peer_averages.json"

    class Decorators():
        """ Subclass containing decorators relating to the player class. """

        @classmethod
        def get_table_index(self, func):
            """ Gets the table index in a soup for an element, given its respective function name. 
            NOTE: this is especially useful because, for example, transferred 
            players have a slightly different layout that pushes multiple elements
            slightly further down the page by the same amount. """
            def inner(self):
                func_name = str(func.__name__)
                table_index = self.index_dict[func_name]
                result = func(self, table_index)
                return result
            return inner

    def __init__(self, player_id):
        super().__init__()

        # Update peer averages file
        util.apply_update_timeago(self.fn_peer_averages, self.__get_peer_averages, weeks=1)

        self.player_id = player_id

        # The same params are used so frequently across this class
        # That I just made it an instance var
        self.params = {'id': player_id}

        # -- Generate table soup ---
        request = self.session.request("GET", "vizualizare_jucator.php?", params=self.params)
        self.tables = make_soup(request).find_all('table')

        # -- If player does not exist, do not bother executing remaining code --
        if not self.__check_player_exists():
            raise Exception("Invalid player")

        # -- Set up Index Dict. ---
        """ The dict tonctains all the indexes of player information. 
        It utilises the get_table_index decorator to distribute these
        indexes across the class's methods. """
        # NOTE: these names MUST correspond with the names of the methods
        index_dict = {
            'player_name': 2, 
            'club': 2,
            'club_id': 2,
            'picture': 4,
            'position': 5,
            'age': 6, 
            'salary': 7, 
            'value': 8, 
            'exp': 9,     
            'nat': 11, 
            'boots': 12,
            'goals': 14, 
            'mom': 14,
            'nat_stats': 14,
            'skill': 16,
            'energy': 19, 
            'morale': 20, 
            'fixed': 23
        }

        # -- Get Transfer listed attribute --
        self.listed = self.__is_listed()

        if not self.listed:
            # If player is not listed, index dict as above is correct
            self.index_dict = index_dict
        else:
            # Increment some values by three because tables are moved # down the page to make way for transfer info
            self.index_dict = { k:(v if k in ('player_name', 'club') else v+3) for k, v in index_dict.items() }

    # -- Executed during __init__() --

    def __get_peer_averages(self):
        """ 
        Calculates the peer averages for each position and age of player 

        For some reason these requests take a long time, so this method 
        should be (and is) called by a util.apply_update method

        r-type: nested dict
        """
        search_results = {position: Search(position) for position in tqdm(self.player_positions)}

        peer_averages = {
            position: {age: search_result.get_avg_stats(specific_age=age, active_teams_only=True) for age in tqdm(range(17,36))} 
            for position, search_result in search_results.items()
        }
        return peer_averages

    @property
    def peer_average(self):
        """
        Returns the peer average primary stats for the player
        Based on their position and age
        """
        # Can only search for players between ages of 17 and 35 (i.e. players that aren't bugged)
        if self.age not in range(17,36):
            raise Exception(f"Invalid age for Search: {self.age}\nCannot determine peer advantage")

        # Open the peer averages file and get the content
        with open(self.fn_peer_averages) as jf:
            content = json.load(jf)
        
        # Grab the appropriate value from the dictionary and return it
        return content[self.position][str(self.age)]

    def __check_player_exists(self):
        """ Verify that player does in fact exists. Returns True/False. """
        if len(self.tables) == 1:
            self.exist = False
            """Could not get player profile for player [ID: {self.player_id}].
            Assumed that player does not exist."""
            return False
        return True

    def __is_listed(self):
        """ Returns True if player is listed, else False """
        try:
            return True if "Current offer" in self.tables[5].find('tr').find('td').text else False
        except:
            string = f"Failed to execute {self.__is_listed.__name__} for {self.player_id}"
            raise Exception(string)

    # -- Player Properties --

    @property
    @Decorators.get_table_index
    def player_name(self, table_index=''):
        """ Get NAME from player profile instance """
        player_string = self.tables[table_index].find_all('td')[1].text # String: player name [ID: 235425]
        formatted_string = player_string.split('[')[0].strip() # String: player name
        return formatted_string

    @property
    @Decorators.get_table_index
    def club_id(self, table_index=''):
        """ Get CLUB_ID from player profile instance """
        href = self.tables[table_index].find_all('td')[2].find('a').get('href')
        return util.get_id_from_href(href)

    @property
    @Decorators.get_table_index
    def club(self, table_index=''):
        """ Get CLUB from player profile instance """
        club = self.tables[table_index].find_all('td')[2].find('a').text
        """ It's possible that a player does not have a club if they club sold them to
        the bank, or they turned 36, and have not yet been deleted from the database.
        Hence return False if not club for clarity. """ 
        return club if club else False

    @property
    @Decorators.get_table_index
    def picture(self, table_index=''):
        """ Get PICTURE (avatar) from player profile instance.
        The player picture is comprised of multiple parts, each referencing an image
        at a different URL. This property returns a tuple of all these links.  """
        return tuple([i.get('src') for i in self.tables[table_index].find_all('img')])

    @property
    @Decorators.get_table_index
    def position(self, table_index=''):
        """ Get POSITION from player profile instance """
        return self.tables[table_index].find('b').text

    @property
    @Decorators.get_table_index
    def age(self, table_index=''):
        """ Get AGE from player profile instance. """
        return int(self.tables[table_index].find('b').text)

    @property
    def birth_year(self):
        """ Returns the actual birth year of a player. e.g. a player of age
        32 at season 30 would have been born in year -2 """
        return self.current_season - self.age

    @property
    @Decorators.get_table_index
    def salary(self, table_index=''):
        """ Get SALARY from player profile instance. """
        string = self.tables[table_index].find_all('tr')[1].find('td').text
        return self.get_value_from_string(string)

    @property
    @Decorators.get_table_index
    def value(self, table_index=''):
        """ Get VALUE from player profile instance. """
        raw_value = self.tables[table_index].find_all('tr')[1].find('td').text.strip()
        return self.get_value_from_string(raw_value)

    @property
    def is_injured(self):
        """ Returns True if player is injured, else False. 
        Does so by searching for a pattern within red text elements on the page. """
        # TODO verify that attributes all still work for injured players
        red_text = [i.text for i in self.tables[16].find_all('font', attrs={'style': 'color:red; font-size: 9px;'})]
        pattern = r"-\d{1,2}%"
        return any([re.match(pattern, i) for i in red_text])

    @property
    @Decorators.get_table_index
    def exp(self, table_index=''):
        """ Get EXPERIENCE from player profile instance. """
        exp = self.tables[table_index].find_all('tr')[1].find('td').text.strip()[0:3]
        return int(exp.split('/')[0])

    @property
    @Decorators.get_table_index
    def nat(self, table_index=''):
        """ Get NATIONALITY from player profile instance. """
        string = str(self.tables[table_index].find_all('tr')[1].find('td').find('a').find('img').get('src'))
        pattern = r"([A-Z]{3,}).[a-z]+"
        return re.findall(pattern, string)[0]

    @property
    @Decorators.get_table_index
    def boots(self, table_index=''):
        """ Get BOOTS from player profile instance.
        A value is always returned since the default boots are 'black'. """
        string = self.tables[table_index].find_all('tr')[1].find('td').find('a').find('img').get('src')
        pattern = r"([A-Z]{3,}).[a-z]+" # TODO explain how this works
        return re.findall(pattern, string)[0].title()

    @property
    @Decorators.get_table_index
    def goals(self, table_index=''):
        """ Get GOALS from player profile instance. """
        tag = self.tables[table_index].find_all('tr')[1].find('td').find_all('b')
        pattern = r"<b>(\d+)</b>" # TODO explain how this works
        gls = [re.findall(pattern, str(i))[0] for i in tag]
        return tuple(int(i) for i in gls)

    @property
    @Decorators.get_table_index
    def mom(self, table_index=''):
        """ Get MOM from player profile instance. """
        tag = self.tables[table_index].find_all('tr')[1].find_all('td')[1].find_all('b')
        pattern = r"<b>(\d+)</b>" # TODO explain how this works
        moms = [re.findall(pattern, str(i))[0] for i in tag]
        return tuple(int(i) for i in moms)

    @property
    @Decorators.get_table_index
    def skill(self, table_index=''):
        """ Get SKILLS from player profile instance. """
        # NOTE explain how this works
        string = str([self.tables[i].find_all('tr')[1].find('td').text for i in range(table_index, table_index+3)])
        pattern = r"([\d\.]+)"
        if self.is_injured:
            player_skills = re.findall(pattern, string)[::2]
        else:        
            player_skills = re.findall(pattern, string)
        # Convert skills to floats
        return tuple([float(i) for i in player_skills])

    @property
    def skill_total(self):
        """ Returns a player's total skill (e.g. 80-75-72 -> 227) """
        return sum(self.skill)

    @property
    @Decorators.get_table_index
    def energy(self, table_index=''):
        """ Get ENERGY from player profile instance. """
        return int(self.tables[table_index].find_all('tr')[1].find('td').text.strip()[:-1])

    @property
    @Decorators.get_table_index
    def morale(self, table_index=''):
        """ Get MORALE from player profile instance. """
        # NOTE explain how this works
        string = str(self.tables[table_index].find_all('tr')[1].find('td').find('img').get('src'))
        pattern = r"_(\d).gif"
        return int(re.findall(pattern, string)[0])

    @property
    @Decorators.get_table_index
    def fixed(self, table_index=''):
        """ Get GOALS from player profile instance. """
        # NOTE explain how this works
        imgs = [self.tables[i].find_all('tr')[1].find('td').find('img').get('src') for i in range(table_index, table_index+5)]
        pattern = r"_(\d).gif"
        return tuple([int(re.findall(pattern, i)[0]) for i in imgs])

    @property
    def talent(self, stars=False):
        """ Uses a rough formula to determine the talent of a player. """
        talent_list = [0.04, 0.048, 0.056, 0.064, 0.08]
        talent_determiner = self.salary / sum(self.skill)
        i = min(talent_list, key=lambda x: abs(x - talent_determiner))
        talent = talent_list.index(i) + 1
        if stars: return f"{chr(9733)} " * talent
        return talent

    def get_form(self):
        """ Returns a tuple of a player's form in the past 15 matches. """
        request = self.session.request("GET", "forma.php?", params=self.params)
        soup = make_soup(request)
        tds = soup.find('table').find_all('tr')[1].find_all('td')[1:]
        b_tags = [float(i.find('b').text) for i in tds]

        """ Reverse the order to most recent match first:
        This is partly because, with players who've played < 15 matches,
        the data fills from the right. So if the list wasn't reversed,
        the alorithm would start from the left and assume that 
        these players hadn't played a match. """
        b_tags = reversed(b_tags)

        form = []
        for match_performance in b_tags:
            if match_performance == 0:
                """ This means that a player didn't play this match
                and therefore won't have played any matches before this.
                Hence, break from the loop. """
                break
            form.append(match_performance)
        return tuple(form)

    @property
    def avg_form(self):
        """ Returns a player's average form over the past 15 matches. """
        form = self.get_form()
        if not sum(form): return False
        avg = sum(form) / len(form)
        return round(avg, 2)

    def get_details(self):
        """ Return all the attributes since cannot do this with __dict__ since
        properties do not count as attributes because life sucks """
        return {
            'id': self.player_id,
            'name': self.player_name,
            'club': self.club,
            'position': self.position,
            'age': self.age,
            'nationality': self.nat,

            'skill_total': self.skill_total,
            'skills': ' - '.join([str(i) for i in self.skill]),
            'fixed': ' - '.join([str(i) for i in self.fixed]),
            'exp': self.exp,

            'salary': self.salary,
            'value': self.value,            
            'talent': self.talent,

            'energy': self.energy,
            'morale': self.morale,
            'boots': self.boots,

            'form': self.avg_form,
            'goals_total': self.goals[1],
            'goals_season': self.goals[0],
            'mom_total': self.mom[1],
            'mom_season': self.mom[0],

            'peer_advantage': self.peer_advantage,
            
            'listed': self.listed
            }

    def print_long_details(self):
        """ Print player's details in a tidy format. """
        details = self.get_details()
        print(f"\n{details['name']} [ID: {details['id']}]")
        del details['id']
        del details['name']
        for k, v in details.items():
            print(f"{k}: {v}")
        print()

    def print_details(self, *args):
        """ Print the player's details based on args provided
        (e.g. "form", "boots -> will give info about the player's form and boots)

        Params:
        - args (strings)

        r-type: None
        """
        details = self.get_details()
        print(f"\n{details['name']} [ID: {details['id']}]")
        del details['id']
        del details['name']

        details = {k:v for k, v in details.items() if k in args}
        for k, v in details.items():
            print(f"{k}: {v}")
        print()

    @property
    def peer_advantage(self):
        """ 
        TODO: move this function to Spider so can be loaded from file instead?

        Calculates the relative peer advanatage of the player
        Based on his primary stats compared to other players of the same age
        Only considers players who belong to clubs with active managers.

        Unfortunately this function takes a long time to execute

        r-type: int (+/-)
        """
        return self.skill_total - self.peer_average
        # search = Search(position=self.position)
        # peer_average = search.get_avg_stats(specific_age=self.age, active_teams_only=True)
        # if not peer_average:
        #     print("Cannot get peer advantage. Too few players to compare to")
        #     return False
        # return sum(self.skill) - peer_average


class UserPlayer(Player):

    def __init__(self, player_id):
        # Get the default information for the player
        super().__init__(player_id)

    @property
    def _profile(self):
        """ Returns the soup of the player's profile page. """
        response = self.session.request("GET", 'profil.php?', params=self.params)
        profile = make_soup(response)
        return profile     

    @property
    def potential(self):
        """ Returns the player's potentials. r-type: int. """
        # Potentials text has these attributes. So use this to get a list of potentials
        green_text = [i.text for i in self._profile.find_all('font', attrs={"color": "#547B22"})]
        # Grab the float of every element in this list of it matches the \d\d pattern
        return tuple([float(i) for i in green_text if re.match(r'\d{2}', i)])

    @property
    def morale_precise(self):
        """ Returns the precise morale of a player (out of 100, rather than 5). r-type: int """
        index = 20 if not self.listed else 23
        onmouseover = str(self._profile.find_all('table')[index].find_all('tr')[1].find('a'))
        return int(re.findall(r"(\d{1,3})%'", onmouseover)[0])

    @property
    def is_trainable(self):
        """ 
        Returns tuple identifying whether a player can be trained in each skill -> True
        (Or if they have reached their potential) -> False

        Example: 80(88)-79(79)-80(81) -> (True, False, True)
        r-type: tuple (of len 3)
        """
        return tuple([False if self.skill[i] == self.potential[i] else True for i in range(3)])

    @property
    def trained_today(self):
        """
        Returns True if a player has been trained today else False
        Does this by going to their profile and attempting to train one of their skills
        But the training of this skill is not confirmed and the player is not actually trained

        r-type: bool
        """
        is_trainable = self.is_trainable
        
        # These players should be caught earlier in Training module
        if not any(is_trainable): raise Exception("Player is maxed out already")

        # Find first trainable skill
        # We need this for subsequent request
        first_positive = is_trainable.index(True)+1

        # Make request to check whether player has been trained today
        response = self.session.request(
            "GET",
            suburl='profil.php?',
            params={'id': self.player_id, 'antrenament': f'A{str(first_positive)}'}
        )
        soup = make_soup(response)

        if soup.find_all('font', text=re.compile("already been trained today")):
            return True
        return False

    @property
    def extra_trained_thisweek(self):
        if self.exp >= 500: raise Exception("Player is maxed out already")
        trainable = bool(self._profile.find('a', attrs={'href': re.compile(r"extra_practice\.php\?id=\d+$")}))
        return not trainable

    def change_name(self):
        """ 
        Change the player's name. r-type: None
        NOTE: this can only be done once!
        """
        if not self._profile.find('a', attrs={'href': re.compile(r"schimba_nume\.php\?id=\d+$")}):
            # Name has already been changed
            return False
        # Confirm change of name
        self.session.request("GET", suburl='schimba_nume.php?', params={'id': self.player_id, 'pag': 'confirma'})


if __name__ == "__main__":
    # search = Search('Goalkeeper')
    player = UserPlayer(150345)
    print(player.extra_trained_thisweek)

    player = UserPlayer(151238)
    print(player.extra_trained_thisweek)
    

    # player = Player(147244)
    # print("Getting peer advantage...")
    # print(player.peer_advantage)


    # search = Search('Defender')
    # print(search.get_avg_stats(19))
