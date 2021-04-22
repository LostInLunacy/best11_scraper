
from time import sleep
from automate import Auto
from morale import MoraleBoost
from training import Training, ExtraTraining
from config import UserSettings
from util import print_divider as print_d
import sys

APP_NAME = "Best11Scraper"
__author__ = "callumEvans (github: punkgazer)"
__version__ = 0.201

USER_SETTINGS = UserSettings()
 

def main():
    auto = Auto()
    
    if USER_SETTINGS.get('daily_bonus', 'on'):
        print_d("> Daily Bonus <")
        auto.get_daily_bonus()

    if USER_SETTINGS.get('bonus_from_partners', 'on'):
        print_d("> Bonus from Partners <")
        auto.get_bonus_from_partners()

    if USER_SETTINGS.get('club_sales', 'on'):
        print_d("> Club Sales <")
        auto.get_club_sales()

    if USER_SETTINGS.get('get_training_points', 'on'):
        print_d("> Training Points <")
        TP_settings = USER_SETTINGS.get_section_items('get_training_points')
        auto.get_training_points(**TP_settings)

    if USER_SETTINGS.get('morale', 'on'):
        print_d("> Morale <")
        morale_boost = MoraleBoost()
        morale_boost.__call__()

    if USER_SETTINGS.get('training', 'on'):
        print_d("> Training <")
        training = Training()
        training.__call__()

    if USER_SETTINGS.get('extra_training', 'on'):
        print_d("> Extra Training <")
        extra_training = ExtraTraining()
        extra_training.__call__()


def menu_system():
    """ The main menu for the program. """

    print()
    print_d(f"Main Menu | {APP_NAME} v{__version__}")


    options = {
        'Quit': sys.exit,
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
    




    