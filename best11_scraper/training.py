
import pendulum

from spider import Best11
from club import UserClub
from util import yn, TimeZones as tz

from time import sleep


user_club = UserClub()


class Training(Best11):

    suburl_training = "antrenament.php?"

    def __init__(self, skill_cutoff=250, peer_advantage_cutoff=-30, energy_warning=100):
        super().__init__()

        # Get user club's players
        self.players = user_club.player_objs

        # Set skill cutoff
        self.skill_cutoff = skill_cutoff
        self.peer_advantage_cutoff = peer_advantage_cutoff
        self.energy_warning = energy_warning

        # Hours until next match
        self.hours_until = self.__hours_until_next_match()

    def __call__(self):
        """ Train players. """
        if not (training_approved := [p for p in self.players if self.assess_player(p)]):
            print("No players to be trained :(")
            return False

        divider = '\n-'
        print(f"\nThe following players have been approved for {self.__class__.__name__}:{divider}{divider.join([i.player_name for i in training_approved])}")

        # Confirmation
        if not yn("Continue?"): return

        # Train all players in list
        [self.train_player(i) for i in training_approved]

    def assess_player(self, player):
        """ Determine whether a player can and should be trained. """

        name = player.player_name

        # Request can be refused. Hence, try; except.
        while True:
            try:
                # -- Assess if player can be trained --
                if not any(player.is_trainable):
                    # If no skills are trainable, player has reached their potential
                    # print(f"{name} is maxed out already!")
                    return False

                # -- Assess if trained today --
                elif player.trained_today:
                    # Player can't be trained twice!
                    # print(f"{name} has already been trained today")
                    return False

                # -- Assess potentials --
                elif sum(player.potential) < self.skill_cutoff:
                    # Player will not be trained; their skills are too low.
                    # print(f"{name} does not meet potential threshold")
                    return False

                # -- Assess peer advantage --
                elif player.peer_advantage < self.peer_advantage_cutoff:
                    # Player will not be trained; they are too far behind their peers
                    # print(f"{name} does not meet peer advantage threshold")
                    return False

                # -- Assess energy for next match if trained --
                elif (final_energy := self.resulting_energy(player)) < self.energy_warning:
                    # Player is tired
                    print(f"""\nWould you like to train {player.player_name} [ID: {player.player_id}]?\
                    They would be at {final_energy}% energy at the start of your next match.""")
                    if not yn():
                        # User does not want tired player trained
                        return False
                    
                # -- Player has passed training assessment --
                return True
            except:
                sleep(.5)

    def player_above_skill_cutoff(self, player):
        """ Returns True if the player is above the skill cutoff, else False. """
        return sum(player.potential) >= self.skill_cutoff

    def __hours_until_next_match(self):
        """ 
        Returns the number of hours between now and the next match.
        rtype: int 
        """
        now = pendulum.now(tz=tz.server)
        next_match = self.get_next_match(string=False)

        # Take off one because you will not regain energy in the final hour
        hours_until = next_match.diff(now).in_hours()
        return hours_until

    def resulting_energy(self, player_obj):
        """ 
        Returns the energy level that the player
        will have after being trained, by the next match. 
        """
        energy = player_obj.energy
        final_energy = (energy + (self.hours_until * 2) - 10)
        return final_energy

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


class ExtraTraining(Training):

    suburl_extra_training = 'extra_practice.php?'
    
    def __init__(self, skill_cutoff=250, peer_advantage_cutoff=-30, energy_warning=100, max_exp=200):
        super().__init__(skill_cutoff, peer_advantage_cutoff)
        self.max_exp = max_exp

    def assess_player(self, player):
        """ Determine whether a player can and should be trained. """

        name = player.player_name

        # Request can be refused. Hence, try; except.
        while True:
            try:
                # -- Assess if player can be trained --
                if player.exp >= 500:
                    # If no skills are trainable, player has reached their potential
                    # print(f"{name} is maxed out already!")
                    return False

                # -- Assess if player's exp too high --
                elif player.exp >= self.max_exp:
                    # print(f"{name} has already reached max exp set for extra training")
                    return False

                # -- Assess if trained this week --
                elif player.extra_trained_thisweek:
                    # Player can't be trained twice!
                    # print(f"{name} has already received extra training this week")
                    return False

                # -- Assess potentials --
                elif sum(player.potential) < self.skill_cutoff:
                    # Player will not be trained; their skills are too low.
                    # print(f"{name} does not meet potential threshold")
                    return False

                # -- Assess peer advantage --
                elif player.peer_advantage < self.peer_advantage_cutoff:
                    # Player will not be trained; they are too far behind their peers
                    # print(f"{name} does not meet peer advantage threshold")
                    return False

                # -- Assess energy for next match if trained --
                elif (final_energy := self.resulting_energy(player)) < 100:
                    # Player is tired
                    print(f"""\nWould you like to train {player.player_name} [ID: {player.player_id}]?\
                    They would be at {final_energy}% energy at the start of your next match.""")
                    if not yn():
                        # User does not want tired player trained
                        return False
                    
                # -- Player has passed training assessment --
                return True
            except:
                sleep(.5)

    def train_player(self, player_obj):
        print(f"Applying training to {player_obj.player_name}") 
        self.session.request(
            "GET",
            suburl=self.suburl_extra_training,
            params=player_obj.params
        )

    def resulting_energy(self, player_obj):
        """ 
        Returns the energy level that the player
        will have after being trained, by the next match. 
        """
        final_energy = super().resulting_energy(player_obj)
        if player_obj.trained_today: final_energy -= 10
        return final_energy


if __name__ == "__main__":
    t = Training()
    t()