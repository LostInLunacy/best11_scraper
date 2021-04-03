"""
    For grabbing available information about a single player (not manager).
"""

import re

# Local imports
from spider import Best11
from session import make_soup
import util


class Player(Best11):
    """ Contains all info pertaining to an individual player (e.g. Leyers Carletto [ID: 302424]),
    given their id. """

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
            'pos': 5,
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
    def pos(self, table_index=''):
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
            'position': self.pos,
            'age': self.age,

            'skill_1': self.skill[0],
            'skill_2': self.skill[1],
            'skill_3': self.skill[2],

            'agg': self.fixed[0],
            'amb': self.fixed[1],
            'int': self.fixed[2],
            'sta': self.fixed[3],
            'vul': self.fixed[4],

            'salary': self.salary,
            'value': self.value,
            'exp': self.exp,
            'nationality': self.nat,
            'talent': self.talent,

            'energy': self.energy,
            'morale': self.morale,

            'form': self.avg_form,
            'goals_total': self.goals[1],
            'goals_season': self.goals[0],
            'mom_total': self.mom[1],
            'mom_season': self.mom[0],

            'boots': self.boots,

            'listed': self.listed
            }

    def print_details(self):
        details = self.get_details()
        print(f"\n{details['name']} [ID: {details['id']}]")
        del details['id']
        del details['name']
        for k, v in details.items():
            print(f"{k}: {v}")
        print()

if __name__ == "__main__":
    x = Player(145677)
    print(x.talent)