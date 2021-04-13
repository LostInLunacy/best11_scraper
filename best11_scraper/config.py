
from configparser import ConfigParser
import util

class UserSettings():
    """
    Purpose
    - For creating and updating user details
    - For updating user preferences
    """

    file_name = "session_files/config.ini"

    def __init__(self):
        self.config_parse = ConfigParser()
        self.config_parse.read(self.file_name)

    class Decorators():
        """ Subclass containing decorators relating to the UserSettings class. """

        @classmethod
        def update_config(self, func):
            """
            Call the function and get the result (True/False)
            If the result is True:
                A change has likely been made
                Hence, update the config file by writing to it
            """
            def inner(self, *args, **kwargs):
                # Get the updated user settings
                updated_settings = func(self, *args, **kwargs)

                if updated_settings:    
                    # Update the file
                    with open(self.file_name, 'w') as cf:
                        self.config_parse.write(cf)

                print()

                return
            return inner

    @Decorators.update_config
    def user_details(self, empty_details=False):

        if empty_details:
            print("Details are incomplete. Please enter them.")
        else:
            # Get current details
            current_details = self.get_all_section('user_details')
            print(f"Current details: {current_details}")
            if not util.yn("Update? "):
                return False

        # Get updated details from user
        username_input = input("Username: ")
        password_input = input("Password: ")

        # User just pressed enter - didn't send any information
        if not any([username_input, password_input]):
            return False

        # Update any fields with information
        if username_input:
            self.config_parse['user_details']['username'] = username_input
        if password_input:
            self.config_parse['user_details']['password'] = password_input
        return True

    def update_preferences(self):
        util.print_divider("Preferences")
        [x() for x in (self.daily_bonus, self.club_sales, self.training_points, self.morale, self.training, self.extra_training)]

    @Decorators.update_config
    def daily_bonus(self):
        collect_daily_bonus = util.yn("Collect daily bonus? ")
        self.config_parse['daily_bonus']['on'] = str(collect_daily_bonus)
        return True

    @Decorators.update_config
    def club_sales(self):
        collect_sales = util.yn("Collect club sales? ")
        self.config_parse['club_sales']['on'] = str(collect_sales)
        return True

    @Decorators.update_config
    def bonus_from_partners(self):
        collect_bfp = util.yn("Collect bonus from partners? ")
        self.config_parse['bonus_from_partners']['on'] = str(collect_bfp)
        return True

    @Decorators.update_config
    def training_points(self):

        # Get current details
        current_details = self.get_all_section('get_training_points')
        print(f"Current details: {current_details}")
        if not util.yn("Update? "):
            return False

        on_input = util.yn("Get training points? ")
        self.config_parse['get_training_points']['on'] = str(on_input)

        # If collecting training points, confirm additional option
        if on_input:
            prompt = "Max TP threshold (or say 'no' for none) "
            tp_threshold = self.get_number_or_no(prompt)

            self.config_parse['get_training_points']['threshold'] = tp_threshold
        return True        

    @Decorators.update_config
    def morale(self):
        talk_to_players = util.yn("Automatically talk to players? ")
        self.config_parse['morale']['on'] = str(talk_to_players)
        return True

    @Decorators.update_config
    def training(self):

        # Get current details
        current_details = self.get_all_section('training')
        print(f"Current details: {current_details}")
        if not util.yn("Update? "):
            return False

        on_input = util.yn("Auto-train players? ")
        self.config_parse['training']['on'] = str(on_input)

        if on_input:
            min_potentials = self.get_number_or_no("Min potentials: ")
            min_peer_avg = self.get_number_or_no("Min peer advantage: ")
            prompt = "Warn you that a player will be BELOW this level of energy for their next match (e.g. 100): "
            energy_warning = self.get_number_or_no(prompt)

            self.config_parse['training']['min_potentials'] = min_potentials
            self.config_parse['training']['min_peer_advantage'] = min_peer_avg
            self.config_parse['training']['energy_warning'] = energy_warning
        return True

    @Decorators.update_config
    def extra_training(self):
        
        # Get current details
        current_details = self.get_all_section('extra_training')
        print(f"Current details: {current_details}")
        if not util.yn("Update? "):
            return False

        on_input = util.yn("Auto-extratrain players? ")
        self.config_parse['training']['on'] = str(on_input)

        if on_input:
            min_potentials = self.get_number_or_no("Min potentials: ")
            min_peer_avg = self.get_number_or_no("Min peer advantage: ")
            prompt = "Warn you that a player will be BELOW this level of energy for their next match (e.g. 100): "
            energy_warning = self.get_number_or_no(prompt)
            max_exp = self.get_number("Max exp you will train up to: ")

            self.config_parse['extra_training']['min_potentials'] = min_potentials
            self.config_parse['extra_training']['min_peer_advantage'] = min_peer_avg
            self.config_parse['extra_training']['energy_warning'] = energy_warning
            self.config_parse['extra_training']['max_exp'] = max_exp
        return True

    @staticmethod
    def get_number_or_no(prompt):
        """
        User input must be either:
        - integer
        - item in util.no_list (i.e. negative response e.g. 'no')

        Params:
            prompt (str) - prompt for the input

        r-type: str (digit) or False
        """
        while True:
            try:
                result = input(prompt)
                if result in util.no_list:
                    result = False
                else:
                    int(result)
            except TypeError:
                print("Please enter an integer or say 'no' for off\n")
            else:
                return result

    @staticmethod
    def get_number(prompt):
        """
        User input must be number

        Params:
            prompt (str) - prompt for the input

        r-type: str (digit)
        """
        while True:
            try:
                result = input(prompt)
                assert result.isdigit()
            except AssertionError:
                print("Please enter an integer\n")
            else:
                return result

    def get_all_section(self, section):
        """ Get all the key, value pairs from a given section of the config file. """
        if section not in self.config_parse.sections():
            raise Exception(f"{section} not in sections:")
        return dict(self.config_parse.items(section))







        
        

    






    

