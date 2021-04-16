
import pendulum

from spider import Best11
from club import UserClub
from util import yn, TimeZones as tz
from config import UserSettings

USER_CLUB = UserClub()
NEXT_MATCH = USER_CLUB.get_next_match(string=False)


class TrainingApprovedList(set):
    """
    An object that consists of players who are approved for training
    It considers factors such as whether a player can be trained,
    As well as factors that affect whether a manager would like to train a player
    - Potentials
    - Current skill related to peers
    - Tiredness
    """
    def __init__(self):
        super().__init__(USER_CLUB.player_objs)
        self.original_list = self.copy()

        self.hours_until_next_match = self.__hours_until_next_match()
        self.settings = self.__get_settings()

        # Run assessments on players, removing any that cannot or shouldn't be trained
        [x() for x in self.assessments]
        
        # Print out info about rejected players
        self.do_printouts()

    def __get_settings(self):
        return {k:v for k, v in UserSettings().get_section_items('training').items() if isinstance(v, (int, float))}

    @property
    def assessments(self):
        return [
            self.get_maxed_out, 
            self.get_trained_already, 
            self.get_min_potentials, 
            self.get_min_peer_advantage, 
            self.get_low_energy
        ]

    def do_printouts(self):
        self.pretty_print(self.trained_already, "Already trained today: ")
        self.pretty_print(self.low_potentials, "Rejected due to low potentials: ")
        self.pretty_print(self.low_peer_advantage, "Rejected due to low peer advantage: ")
        self.pretty_print(self.low_energy, "Rejected due to low energy: ")
        self.pretty_print(self, "Ready for training: ")

    @staticmethod
    def pretty_print(items, title):
        if not items:
            return
        print(title)
        [print(f"- {str(i)}") for i in items]
        print()

    def get_maxed_out(self):
        self.maxed_out = {i for i in self if not any (i.is_trainable)}
        self -= self.maxed_out

    def get_trained_already(self):
        self.trained_already = {i for i in self if i.trained_today}
        self -= self.trained_already

    def get_min_potentials(self):
        if not (min_potential_setting := self.settings.get('min_potentials')):
            self.low_potentials = set()
            return
        self.low_potentials = {i for i in self if sum(i.potential) < min_potential_setting}
        self -= self.low_potentials

    def get_min_peer_advantage(self):
        if not (min_peer_advantage := self.settings.get('min_peer_advantage')):
            self.low_peer_advantage = set()
            return
        self.low_peer_advantage = {i for i in self if i.peer_advantage < min_peer_advantage}
        self -= self.low_peer_advantage

    def get_low_energy(self):
        if not (energy_warning := self.settings.get('energy_warning')):
            self.energy_warning = set()
            return

        def energy_fail(player):
            if (final_energy := self.resulting_energy(player)) < energy_warning:
                # Player is tired
                print(f"""\nWould you like to train {player.player_name} [ID: {player.player_id}]?\
                They would be at {final_energy}% energy at the start of your next match.""")
                if not yn():
                    # User does not want tired player trained
                    return False
            return True
        self.low_energy = {i for i in self if not energy_fail(i)}
        self -= self.low_energy

    def __hours_until_next_match(self):
        """ 
        Returns the number of hours between now and the next match.
        rtype: int 
        """
        now = pendulum.now(tz=tz.server)

        # Take off one because you will not regain energy in the final hour
        hours_until = NEXT_MATCH.diff(now).in_hours()
        return hours_until

    def resulting_energy(self, player_obj):
        """ 
        Returns the energy level that the player
        will have after being trained, by the next match. 
        """
        energy = player_obj.energy
        final_energy = (energy + (self.hours_until_next_match * 2) - 10)
        return final_energy  
        
class Training(Best11):

    suburl_training = "antrenament.php?"

    def __init__(self):
        super().__init__()
        self.players = self.get_players()

    def get_players(self):
        return TrainingApprovedList()

    def __call__(self):
        if not self.players:
            print("No players to be trained :(")
            return False

        divider = '\n- '
        # TODO add player positon to string
        # print(f"\nThe following players have been approved for {self.__class__.__name__}:{divider}{divider.join([i.player_name for i in self.players])}")

        # Confirmation
        if not yn("Continue?"): return

        # Train all players in list
        [self.train_player(i) for i in self.players]

    def train_request(self, player_obj, skill_num):
        """
        Train a player, given the player_object and the skill_id for them to train
        (e.g. for a midfielder, passing = 1, creativity = 2, etc.)
        """
        params = {'id': player_obj.player_id, 'atribut': f'A{str(skill_num+1)}'}
        print(f"Applying training to {player_obj.player_name}") 
        self.session.request(
            "GET",
            self.suburl_training,
            params=params
            )

    def train_player(self, player_obj):
        """ Returns a func based on a player's position to train that player. """

        # Get the appropriate function for the player
        func = {
            'Goalkeeper': self.train_gk,
            'Defender': self.train_df,
            'Midfielder': self.train_mf,
            'Striker': self.train_fw
        }[player_obj.position]

        # Get skill to train
        skill_to_train = func(player_obj)

        # Train skill
        self.train_request(player_obj, skill_to_train)

    def train_gk(self, player_obj):
        """ Settings for training goalkeepers. 
        Returns the chosen skill to train. """
        is_trainable = player_obj.is_trainable
        hand, refl, pen = (0,1,2)
        skill_to_train = None

        if is_trainable[refl]:
            skill_to_train = refl
        elif is_trainable[hand]:
            skill_to_train = hand
        elif is_trainable[pen]:
            skill_to_train = pen

        if skill_to_train is None:
            raise Exception(f"Could not find skill to train for {player_obj.player_name}")
        return skill_to_train

    def train_df(self, player_obj):
        """ Settings for training defenders. 
        Returns the chosen skill to train. """
        is_trainable = player_obj.is_trainable
        tack, mark, head = (0,1,2)
        skill_to_train = None
        skill = player_obj.skill
        
        if is_trainable[tack]:
            if is_trainable[mark]:
                skill_to_train = skill.index(min([skill[tack], skill[mark]]))
            else:
                skill_to_train = tack
        elif is_trainable[mark]:
            skill_to_train = mark
        elif is_trainable[head]:
            skill_to_train = head

        if skill_to_train is None:
            raise Exception("Could not find skill to train.")
        return skill_to_train

    def train_mf(self, player_obj):
        """ Settings for training defenders. 
        Returns the chosen skill to train. """
        is_trainable = player_obj.is_trainable
        pas, creat, tech = (0,1,2)
        skill_to_train = None
        skill = player_obj.skill

        if is_trainable[(i:= pas)]:
            if is_trainable[(j:= creat)]:
                skill_to_train = skill.index(min([skill[i], skill[j]]))
            else:
                skill_to_train = pas
        elif is_trainable[creat]:
            skill_to_train = creat
        elif is_trainable[tech]:
            skill_to_train = tech

        if skill_to_train is None:
            raise Exception("Could not find skill to train.")
        return skill_to_train

    def train_fw(self, player_obj):
        """ Settings for training goalkeepers. 
        Returns the chosen skill to train. """
        is_trainable = player_obj.is_trainable
        fini, tech, head = (0,1,2)
        skill_to_train = None

        if is_trainable[fini]:
            skill_to_train = fini
        elif is_trainable[tech]:
            skill_to_train = tech
        elif is_trainable[head]:
            skill_to_train = head

        if skill_to_train is None:
            raise Exception(f"Could not find skill to train for {player_obj.player_name}")
        return skill_to_train

class ExtraTrainingApprovedList(TrainingApprovedList):

    def __init__(self):
        super().__init__()

    def __get_settings(self):
        return {k:v for k, v in UserSettings().get_section_items('extra_training').items() if isinstance(v, (int, float))}

    @property
    def assessments(self):
        return [
            self.get_maxed_out,
            self.get_high_exp,
            self.get_trained_already,
            self.get_min_potentials, 
            self.get_min_peer_advantage, 
            self.get_low_energy
        ]

    def do_printouts(self):
        self.pretty_print(self.trained_already, "Already trained this week: ")
        self.pretty_print(self.low_potentials, "Already reached EXP threshold: ")
        self.pretty_print(self.low_potentials, "Rejected due to low potentials: ")
        self.pretty_print(self.low_peer_advantage, "Rejected due to low peer advantage: ")
        self.pretty_print(self.low_energy, "Rejected due to low energy: ")
        self.pretty_print(self, "Ready for training: ")

    def get_trained_already(self):
        self.trained_already = {i for i in self if i.extra_trained_thisweek}
        self -= self.trained_already

    def get_high_exp(self):
        if not (max_exp_setting := self.settings.get('max_exp')):
            self.energy_warning = set()
            return
        self.max_exp = {i for i in self if i.exp > max_exp_setting}
        self -= self.max_exp

class ExtraTraining(Training):

    suburl_extra_training = 'extra_practice.php?'
    
    def __init__(self):
        super().__init__()

    def get_players(self):
        return ExtraTrainingApprovedList()

    def __call__(self):
        super().__call__()

    def train_player(self, player_obj):
        print(f"Applying training to {player_obj.player_name}") 
        self.session.request(
            "GET",
            suburl=self.suburl_extra_training,
            params=player_obj.params
        )


if __name__ == "__main__":
    TrainingApprovedList()


