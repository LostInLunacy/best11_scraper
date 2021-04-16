
from configparser import ConfigParser
import util

def update_config(func):
    def inner(*args, **kwargs):
        instance = args[0]
        updated_settings = func(*args, **kwargs)
        if updated_settings:
            instance.save_file()
    return inner

class UserSettings(ConfigParser):
    """
    Purpose
    - For creating and updating user details
    - For updating user preferences
    """

    file_name = "session_files/config.ini"

    def __init__(self):
        super().__init__()
        self.read(self.file_name)

    # class Decorators():
    #     """ Subclass containing decorators relating to the UserSettins class. """

    #     @classmethod
    #     def update_config(cls, func):
    #         """
    #         Call the function and get the result (True/False)
    #         If the result is True:
    #             A change has likely been made
    #             Hence, save (i.e. write to) the file
    #         """
    #         def inner(*args, **kwargs):
    #             # Get updated user settings
    #             updated_settings = func(*args, **kwargs)
    #             if updated_settings: self.save_file()
    #         return inner

    def save_file(self):
        """ Save the config file. """
        with open(self.file_name, 'w') as cf:
            self.write(cf)

    def get(self, section, item, **kwargs):
        if section not in self.sections():
            print(f"Invalid section: {section}")
        item = super().get(section, item, **kwargs)
        if not item:
            return False
        if self.is_digit_abs(item):
            return int(item)
        elif item in ('True', 'False', 'None'):
            return self.str_to_bool(item)
        return item

    @staticmethod
    def str_to_bool(string):
        if not string:
            raise Exception("Empty string")
        string = string.lower()
        
        if string == 'none': 
            return None
        elif string == 'true':
            return True
        elif string == 'false':
            return False
        else:
            raise Exception(f"String >{string}< couldn't be converted to bool")

    def get_section_items(self, section, omit=('on')):
        if section not in self.sections():
            raise Exception(f"Invalid section: {section}")

        options = list(self[section].keys())
        options_items = {k:self.get(section, k) for k in options if k not in omit}
        return options_items
        
    @staticmethod
    def is_digit_abs(text):
        if text.replace('-', '').isdigit(): return True
        return False

    @update_config
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
            self['user_details']['username'] = username_input
        if password_input:
            self['user_details']['password'] = password_input
        return True

    def update_preferences(self):
        util.print_divider("Preferences")
        [x() for x in (self.daily_bonus, self.club_sales, self.training_points, self.morale, self.training, self.extra_training)]

    @update_config
    def daily_bonus(self):
        collect_daily_bonus = util.yn("Collect daily bonus? ")
        self['daily_bonus']['on'] = str(collect_daily_bonus)
        return True

    @update_config
    def club_sales(self):
        collect_sales = util.yn("Collect club sales? ")
        self['club_sales']['on'] = str(collect_sales)
        return True

    @update_config
    def bonus_from_partners(self):
        collect_bfp = util.yn("Collect bonus from partners? ")
        self['bonus_from_partners']['on'] = str(collect_bfp)
        return True

    @update_config
    def training_points(self):

        # Get current details
        current_details = self.get_all_section('get_training_points')
        print(f"Current details: {current_details}")
        if not util.yn("Update? "):
            return False

        on_input = util.yn("Get training points? ")
        self['get_training_points']['on'] = str(on_input)

        # If collecting training points, confirm additional option
        if on_input:
            max_tp = self.get_number_or_no("Max TP threshold (or say 'no' for none): ")
            only_slot = self.get_number_or_no("Only train this slot: (or say 'no' to train both):")

            self['get_training_points']['max_tp'] = max_tp
            self['get_training_points']['only_slot'] = only_slot
        return True        

    @update_config
    def morale(self):
        talk_to_players = util.yn("Automatically talk to players?")
        self['morale']['on'] = str(talk_to_players)
        return True

    @update_config
    def training(self):

        # Get current details
        current_details = self.get_all_section('training')
        print(f"Current details: {current_details}")
        if not util.yn("Update? "):
            return False

        on_input = util.yn("Auto-train players? ")
        self['training']['on'] = str(on_input)

        if on_input:
            min_potentials = self.get_number_or_no("Min potentials:")
            min_peer_avg = self.get_number_or_no("Min peer advantage:")
            prompt = "Warn you that a player will be BELOW this level of energy for their next match (e.g. 100):"
            energy_warning = self.get_number_or_no(prompt)

            self['training']['min_potentials'] = min_potentials
            self['training']['min_peer_advantage'] = min_peer_avg
            self['training']['energy_warning'] = energy_warning
        return True

    @update_config
    def extra_training(self):
        
        # Get current details
        current_details = self.get_all_section('extra_training')
        print(f"Current details: {current_details}")
        if not util.yn("Update? "):
            return False

        on_input = util.yn("Auto-extratrain players? ")
        self['training']['on'] = str(on_input)

        if on_input:
            min_potentials = self.get_number_or_no("Min potentials: ")
            min_peer_avg = self.get_number_or_no("Min peer advantage: ")
            prompt = "Warn you that a player will be BELOW this level of energy for their next match (e.g. 100): "
            energy_warning = self.get_number_or_no(prompt)
            max_exp = self.get_number("Max exp you will train up to: ")

            self['extra_training']['min_potentials'] = min_potentials
            self['extra_training']['min_peer_advantage'] = min_peer_avg
            self['extra_training']['energy_warning'] = energy_warning
            self['extra_training']['max_exp'] = max_exp
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
                result = input(f"{prompt}\n>")
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
                result = input(f"{prompt}\n>")
                assert result.isdigit()
            except AssertionError:
                print("Please enter an integer\n")
            else:
                return result

    def get_all_section(self, section):
        """ Get all the key, value pairs from a given section of the config file. """
        if section not in self.sections():
            raise Exception(f"Invalid section: {section}")
        return dict(self.items(section))