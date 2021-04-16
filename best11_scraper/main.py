
from time import sleep
from automate import Auto
from morale import MoraleBoost
from training import Training
from config import UserSettings
from util import print_divider as print_d

APP_NAME = "Best11Scraper"
__author__ = "callumEvans (github: punkgazer)"
__version__ = 0.201

USER_SETTINGS = UserSettings()
 

def main():
    auto = Auto()
    
    if USER_SETTINGS.get('daily_bonus', 'on'):
        print_d("Getting daily bonus...")
        auto.get_daily_bonus()

    if USER_SETTINGS.get('bonus_from_partners', 'on'):
        print_d("Getting bonus from partners...")
        auto.get_bonus_from_partners()

    if USER_SETTINGS.get('club_sales', 'on'):
        print_d("Getting club sales...")
        auto.get_club_sales()

    # NOTE need way of determining if already been done
    # if USER_SETTINGS.get('get_training_points', 'on'):
    #     print_d("Getting TP...")
    #     TP_settings = USER_SETTINGS.get_section_items('get_training_points')
    #     auto.get_training_points(**TP_settings)

    if USER_SETTINGS.get('morale', 'on'):
        print_d("Getting morale boost...")
        morale_boost = MoraleBoost()
        morale_boost.__call__()

    if USER_SETTINGS.get('training', 'on'):
        training = Training()
        training.__call__()

    # if USER_SETTINGS.get('extra_training', 'on'):
    #     print_d("Performing extra training...")
    #     et_settings = USER_SETTINGS.get_section_items('extra_training')
    #     extra_training = ExtraTraining()
    #     extra_training.__call__(**et_settings)


def menu_system():
    """ The main menu for the program. """

    print()
    print_d(f"Main Menu | {APP_NAME} v{__version__}")

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
    




    