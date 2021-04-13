
import re

from spider import Best11
from session import make_soup
import util

class Match(Best11):
    """ Contains all information pertaining to an individual match
    Takes a match_id. """

    suburl_match = 'meci.php?'

    def __init__(self, match_id):
        super().__init__()
        self.match_id = match_id
        self.soup_dict = self.__get_matchpage_soup()

    @property
    def params(self):
        """ Commonly used parameters for making requests. """
        return {'id': self.match_id}

    def __get_matchpage_soup(self):
        """ 
        Gets the soup
        Called by __init__ to avoid repeat calling
        Divides soup up into commonly used sections
        r-type: dict
        """

        # -- Make request to the match's page --
        response = self.session.request(
            "GET",
            suburl=self.suburl_match,
            params=self.params
        )
        soup = make_soup(response)

        # -- Check that match has been played --
        match_played = bool((table:= soup.find('table')).find('tr').find_all('td')[1].text == "Final Score")
        if not match_played:
            raise Exception("Match has not been played yet")

        # -- Create soup dict for commonly used soup --
        soup_dict = {
            'table': table,
            'game_events_table': soup.find_all('table')[2],
        }
        soup_dict['rows'] = soup_dict['table'].find_all('tr')[1:4]
        soup_dict['attweath'] = soup_dict['game_events_table'].find_all('tr')[-2].text
        soup_dict['sub_table'] = soup_dict['rows'][1].find('table')
        soup_dict['home_stats'] = soup_dict['rows'][1].find('td')
        soup_dict['away_stats'] = soup_dict['rows'][1].find_all('td')[-1]
        return soup_dict

    @property
    def clubs(self):
        """ 
        Returns the teams in the match. 
        r-type: tuple
        r-format: ('Solent City', 'LOUFC')
        """
        row = self.soup_dict['rows'][0]
        return tuple([
            row.find_all('td')[0].text,
            row.find_all('td')[-1].text
        ])

    @staticmethod
    def __get_team_id_from_team_search(soup, club):
        index = 1
        while True:
            try:
                a_tag = soup.find_all('table')[2].find_all('tr')[index].find_all('td')[2].find('a')
            except:
                raise Exception(f"Unable to find team: {club}")
            team_name = a_tag.text
            if team_name == club:
                href = a_tag.get('href')
                return util.get_id_from_href(href)
            index += 1

    @property
    def club_ids(self):
        """ 
        Returns the club ids for the two clubs.
        Using the club_id_from_club method from the parent Best11 class
        r-type: tuple
        r-format: (300, 416)
        """
        return tuple([self.club_id_from_club(name) for name in self.clubs])

    @property
    def match_result(self):
        """
        Returns the match result
        r-type: tuple
        r-format: (1,2) -> a 1-2 loss for the home side
        """
        row = self.soup_dict['rows'][0]
        match_tds = row.find_all('td')[2:4]
        scores = tuple(i.find('img').get('src') for i in match_tds)
        return tuple(int(re.findall(r'\d{1,2}', i)[0]) for i in scores)

    @property
    def teamsheets(self):
        """
        Returns the teamsheets for the two clubs.
        r-type: tuple containing two lists: one for home; one for away
        r-format: (['Pearce Reading', 'Roy Banks',...], ['Arthur Flitcroft,...])
        """
        home_roster = [a.text.replace("\ufeff", "") for a in self.soup_dict['game_events_table'].find_all('tr')[-4].find_all('a')]
        away_roster = [a.text.replace("\ufeff", "") for a in self.soup_dict['game_events_table'].find_all('tr')[-5].find_all('a')]
        return tuple([home_roster, away_roster])

    @property
    def attendance(self):
        """ Returns the match attendance. r-type: int """
        attendance_pattern = r"(\d{3,6}) spectators"
        return int(re.findall(attendance_pattern, self.soup_dict['attweath'])[0])

    @property
    def weather(self):
        """ Returns the weather. r-type: str """
        weather_pattern = r"in this ([a-z\s]+) day"
        return re.findall(weather_pattern, self.soup_dict['attweath'])[0]

    @property
    def formations(self):
        """ 
        Returns the formations of each team. 
        r-format: ('5-4-1', '5-3-2')
        """
        formations = tuple(re.findall(r"(\d-\d-\d)", str(self.soup_dict['game_events_table'])))
        return tuple(reversed(formations))

    @property
    def possession(self):
        """ 
        Returns the possession of each team. 
        r-format: (49, 51)
        """
        row = self.soup_dict['rows'][1]
        string = row.find_all('td')[1].text
        possession_pattern = r"Possession:(\d{0,3})% - (\d{0,3})"
        return tuple(int(i) for i in re.findall(possession_pattern, string)[0])

    @property
    def avg_age(self):
        """
        Returns the average age of each team
        This is only recorded to nearest int. Hence ints are used, whereas mood and energy use floats
        r-format: (21.9, 26.6) 
        """
        return tuple(float(i.text) for i in self.soup_dict['sub_table'].find_all('tr')[1].find_all('td')[1:])

    @property
    def avg_mood(self):
        """
        Returns the average mood of each team
        r-format: (89.5, 80.7)
        """
        return tuple(float(i.text) for i in self.soup_dict['sub_table'].find_all('tr')[2].find_all('td')[1:])

    @property
    def avg_energy(self):
        """
        Returns the average energy for each team
        r-format: (96.9, 100)
        """
        return tuple(float(i.text) for i in self.soup_dict['sub_table'].find_all('tr')[3].find_all('td')[1:])
    

    @property
    def individual_stats(self):
        """
        Returns the individual stats for each team
        Individual stats means the performances of each individual within each team's roster
        r-type: tuple containing two dicts
        r-format: ({'Dalibor Petřík': 100.97, 'Steven Baret': 72.33...}, {{'Josh Compton': 113.23,...})
        """

        def get_individual_stats(data):
            """
            Returns the individual stats for one of the two teams
            r-type: dict
            """
            results = {}

            indivstat_pattern = r"popup\('(.*)<br>\[<b>(\d{1,3}\.\d{2})"
            for link in data:
                tmp = link.get('onmouseover')
                try:
                    player, performance = re.findall(indivstat_pattern, tmp)[0]
                    results[player] = round(float(performance),2)
                except:
                    pass
            if len(results) != 11:
                raise Exception("Players != 11")
            return results

        # Call function above for both teams in the game. Return the result
        return tuple(get_individual_stats(i.find_all('a')) for i in (self.soup_dict['home_stats'], self.soup_dict['away_stats']))

    @property 
    def collective_stats(self):
        """
        Returns the collective stats for each team
        Collective stats means the ratings you get for GK/DF, MF and FW (e.g. 15-9-13)
        r-type: tuple
        r-format: ([15, 8, 14], [17, 14, 15])
        """

        def get_collective_stats(data):
            """ 
            Returns the collective stats given fonts
            r-type: list of len 3
            """
            collective_stats_pattern = r"(\d{1,2})/20"
            tmp = str(data.find_all('font'))
            result = [int(i) for i in re.findall(collective_stats_pattern, tmp)]
            if len(result) != 3: 
                raise Exception(f"Invalid collective stats: {result}")
            return result

        # Call function above for both teams in the game. Return the result
        return tuple(get_collective_stats(i) for i in (self.soup_dict['home_stats'], self.soup_dict['away_stats']))

    @staticmethod
    def __get_scoresheet(home_or_away):
        """ Returns a scoresheet given some td data """ 
        players = [j.text.replace("'", "") for j in home_or_away.find_all('a')]
        when_scored = [int(j.text[1:]) for j in home_or_away.find_all('b')]
        results = {}
        for i in range(len(players)):
            if players[i] in results.keys():
                results[players[i]].append(when_scored[i])
            else:
                results[players[i]] = [when_scored[i]]
        return results

    @property
    def scoresheet(self):
        """ Returns the match's scoresheet. """
        tds = self.soup_dict['table'].find_all('tr')[7].find_all('td')
        home = self.__get_scoresheet(tds[0])
        away = self.__get_scoresheet(tds[-1]) if len(tds) == 2 else False
        return tuple([home, away])

    @staticmethod
    def __get_best_performer(stats):
        """ Get the best performer for a side. """
        best_player = max(stats, key=stats.get)
        return tuple([best_player, stats[best_player]])

    @property
    def best_performers(self):
        """ Get the best performers - still need to design mom and mot. """
        home_stats, away_stats = self.individual_stats
        best_home = self.__get_best_performer(home_stats)
        best_away = self.__get_best_performer(away_stats)
        return tuple([best_home, best_away])

    def get_match_info_dict(self):
        """ Return all data besides best performers. """
        initial_data = []
        for i in range(2):
            initial_data.append(
                {
                'club_id': self.club_ids[i],
                'club': self.clubs[i],
                'formation': self.formations[i],
                'teamsheet': self.teamsheets[i],
                'possession': self.possession[i],
                'gf': self.match_result[i],
                'scoresheet': self.scoresheet[i],
                'avg_age': self.avg_age[i],
                'avg_mood': self.avg_mood[i],
                'avg_energy': self.avg_energy[i], 
                }
            )

        # Update home with attendance, weather
        initial_data[0].update(
            {
                'attendance': self.attendance,
                'weather': self.weather                
            }
        )
        return tuple([*initial_data])