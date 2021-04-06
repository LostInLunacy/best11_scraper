
import random
import re

from session import make_soup
from spider import Best11
from player import UserPlayer
from club import UserClub
import util

class MoraleBoost(Best11):
    """ Automate the process of raising your players' happiness. """

    # Each chat has its own id
    # chat_dict{} is called to get id from chat str
    chat_dict = {
            "I like your enthusiasm": 1,
            "I'm glad that you're happy": 2,
            "Is there something wrong with you?": 3,
            "Stop complaining!": 4,
            "Let's have some beers": 5,
            "You're free to be sad": 6,
            "I'm really lucky to have you in the squad": 7,
            "Your performance is gratifying": 8,
            "I'm pleased with your work": 9,
            "I'm not satisfied with your game": 10,
            "If I don't see an improvement, you're out": 11,
            "It's time to leave!": 12
        }

    def __init__(self):
        super().__init__()
        self.get_players()

    def __apply_happiness(self, player_id, chat):
        response = self.session.request(
            "GET", 
            suburl="interactiune.php?", 
            params={'id': player_id, 'replica': chat}
        )
        soup = make_soup(response)
        if soup.find_all(text=re.compile(r'^You already had a chat with this player today')):
            return False

        text = soup.find_all('div')[4].text
        change = re.findall(r"(\d{1,2})%", text)
        try:
            change = int(change[0])
        except IndexError:
            # No change
            return 0
        else:
            return change

    def __call__(self):
        
        def talk(player):
            name = player.player_name

            if player.morale_precise == 100:
                # Already at 100%
                return False
            elif player.morale == 5:
                chat_line = random.choice(["I'm glad that you're happy", "I like your enthusiasm"])
            elif player.morale == 4:
                chat_line = "I'm glad that you're happy"
            else:
                print(f"Could not raise morale for unhappy player: {name}")
                # Player has low mood
                return False
            
            chat = self.chat_dict[chat_line]
            if (change := self.__apply_happiness(player.player_id, chat)) is False:
                print(f"You already spoke to {name} today!")
                # Can't boost morale twice
                return False

            if not change:
                print(f"{name} didn't receive a boost! :(")
            else:
                print(f"{name} recieved a boost of {change}%")

            return True

        # Show morale before
        self.print_avg_morale("Morale before: ")

        # Talk to players and get the total number of talks done
        talked_to = sum([talk(i) for i in self.players])

        # If unable to talk to any players, report no change
        if not talked_to:
            print("\nNo change")
            return False
        else:
            print(f"\nSuccessfully talked to {talked_to} players")

        # Refresh players list to get up to date morale
        self.get_players()

        # Show morale after
        self.print_avg_morale("Morale after: ")

    def get_players(self):
        """ Updates the instance with a list of the user's players as player objects. """
        self.players = UserClub().player_objs
    
    @property
    def avg_morale(self):
        return util.mean_avg([i.morale_precise for i in self.players], r=3)

    def print_avg_morale(self, msg):
        """ Prints out the mean avg percent happiness of the instance's players. """
        util.print_divider(f"{msg}{self.avg_morale:.2f}%")


    

