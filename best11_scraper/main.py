
from time import sleep

from automate import Auto
from morale import MoraleBoost
from training import Training, ExtraTraining
from config import UserSettings
from util import print_divider as print_d

USER_SETTINGS = UserSettings()


def main():
    auto = Auto()
    
    if USER_SETTINGS.config_parse.getboolean('daily_bonus', 'on'):
        print_d("Daily bonus.")
        auto.get_daily_bonus()

    if USER_SETTINGS.config_parse.getboolean('bonus_from_partners', 'on'):
        print_d("Getting bonus from partners...")
        auto.get_bonus_from_partners()

    if USER_SETTINGS.config_parse.getboolean('club_sales', 'on'):
        print_d("Getting club sales...")
        auto.get_club_sales()

    if USER_SETTINGS.config_parse.getboolean('get_training_points', 'on'):
        print_d("Getting TP...")
        threshold = USER_SETTINGS.config_parse.get('get_training_points', 'threshold')
        auto.get_training_points()

    if USER_SETTINGS.config_parse.getboolean('morale', 'on'):
        print_d("Getting morale boost...")
        morale_boost = MoraleBoost()
        morale_boost.__call__()

    if USER_SETTINGS.config_parse.getboolean('training', 'on'):
        print_d("Performing training...")
        training_settings = {k:v for k, v in USER_SETTINGS.get_all_section('training').items() if k != 'on'}
        training = Training()
        training.__call__(**training_settings)

    if USER_SETTINGS.config_parse.getboolean('extra_training', 'on'):
        print_d("Performing extra training...")
        et_settings = {k:v for k, v in USER_SETTINGS.get_all_section('extra_training').items() if k != 'on'}
        extra_training = ExtraTraining()
        extra_training.__call__(**et_settings)


def menu_system():
    """ The main menu for the program. """

    options = {
        'Quit': quit,
        'Run program': main,
        'Preferences': USER_SETTINGS.update_preferences,
        'Change login details': USER_SETTINGS.user_details
        }

    keys = list(options.keys())
    options_range = range(len(keys))

    for i in options_range:
        print(f"{i}. {keys[i]}")
    
    while True:
        
        try:
            user_input = int(input("\n> "))
            if not user_input in options_range:
                print("Response outside of range. Please try again.")
                continue
        except:
            print("Non-integer response. Please try again.")
        else:
            options[keys[user_input]]()
            menu_system()


if __name__ == "__main__":
    menu_system()




    