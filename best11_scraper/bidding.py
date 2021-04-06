"""
    For getting information about transfer listed players
    And scripts to automate bidding on a given player up to a specific amount
"""


# Imports
from time import sleep

# Local Imports
from club import Club
from player import Player
from spider import Best11
from session import make_soup
import util


USER_CLUB = Club(manager="user")


class ListedPlayer(Player):
    
    def __init__(self, player_id):
        super().__init__(player_id)
        if not self.listed:
            raise Exception("Player not listed")

    @property
    def __transfer_info(self):
        if not self.listed:
            print("Cannot get bidding info for unlisted player!")
            return False

        request = self.session.request("GET", suburl="vizualizare_jucator.php?", params=self.params)
        table = make_soup(request).find_all('table')[5]

        current_offer = self.get_value_from_string(table.find('td').text)
        current_bidder = table.find('a').text
        deadline = table.find_all('td')[2].find('b').text

        return {
            'current_offer': current_offer,
            'current_bidder': current_bidder,
            'deadline': deadline
        }

    def bid(self):
        """ Place a bid on the player. """
        if not self.listed:
            raise Exception("Tried to bid on unlisted player")
        self.session.request("GET", suburl="licitatie.php?", params=self.params)

    def repeat_bid(self, max_bid='10.000 C', interval=30):
        """ Repeatedly bid for a player while they're on the market
        and do not exceed your maximum bid. """

        user_club_name = USER_CLUB.club_name

        try:
            max_bid = self.get_value_from_string(max_bid)
        except:
            raise Exception(f"Could not convert {max_bid} to a number value")

        assert max_bid >= self.value

        while True:

            if not (info := self.__transfer_info):
                # Player is no longer listed
                return
            if info['current_offer'] + 20 > max_bid:
                # Player bidding has exceeded your maximum bid
                print("You have lost the bidding war!")
                return

            ## You are actively bidding
            if (current_bidder := info['current_bidder']) == user_club_name:
                print("You are the current bidder!")
            else:
                print(f"\nNew bid from {current_bidder}")
                # You are not the current bidder. Make bid
                print("Making higher bid...")
                self.bid()

            # Wait 10 seconds before repeating
            sleep(interval)

class TransferList(Best11):
    def __init__(self):
        super().__init__()
        player_ids = util.flat_list([self.request_listed_players(i) for i in range(1,5)])
        self.tl_players = [Player(i) for i in player_ids]

    def request_listed_players(self, position):
        request = self.session.request(
            "POST",
            suburl='lista_transferuri.php',
            data={
                'varsta': 0, # Age
                'pozitie': position,
                'A1': 10, # Skill 1
                'A2': 10, # Skill 2
                'A3': 10, # Skill 3
                'AMB': 1, # Ambition
                'INT': 1, # Intelligence
                'REZ': 1, # Stamina
                'AGR': 5, # Aggression (highest considered worst)
                'VUL': 5, # Vulnerability (highest considered worst)
            }
        )

        soup = make_soup(request)
        player_ids = [util.get_id_from_href(i.get('action')) for i in soup.find_all('form')]
        return player_ids

    def __call__(self, min_talent=1, max_age=17, min_skill=10*3, peer_advantage=-200):
        tl_players = self.tl_players
        return [i for i in tl_players if i.talent >= min_talent and i.age <= max_age and i.skill_total >= min_skill and (not i.peer_advantage or i.peer_advantage >= peer_advantage)]

if __name__ == "__main__":
    t = TransferList()
    results = t(min_talent=5, max_age=31, min_skill=45*3, peer_advantage=-50)

    for i in results:
        i.print_details('club', 'position', 'age', 'skills', 'fixed', 'talent', 'form', 'peer_advantage')
