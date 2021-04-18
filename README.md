# best11_scraper
Scrapes from and makes requests to [best11.org](https://best11.org/)

Created by callumEvans (Solent City)

# Installation:
Installer: [here](https://github.com/punkgazer/best11_scraper/releases/download/v.201/best11_scraper.exe)

# How to Run
Once installed, navigate to inside the best11_scraper folder twice and locate the executable file (labelled main)
This is what is used to run the program

# How to use
Once the program starts it will ask you for your login details. This is necessary in order to make requests to the website
regarding information that is only accessible to specific users.

Once logged in, you will be greeted with a small menu. By default, everything is off. So you will need to go through the preferences
section and adjust the options as you see fit.

## The preferences
- **Daily Bonus**: collect daily bonus
- **Club Sales**: collect club sales
- **Collect Training Points**: collect TP
  - **Max TP**: stops collecting TP after this amount. 
    - NOTE that input amount will be multiplied by 1000 (e.g. 350 -> 350.000 TP)
  - **Only Slot**: only collects TP from the first or second technical staff member
- **Morale**: raise morale of players by talking to them
- **Training**: train players
  - **Min Potentials**: exclude players if the sum of their potentials doesn't meet this threshold
  - **Min Peer Advantage**: exclude players if their peer advantage is below this threshold
    - NOTE: peer advantage value represents how far ahead/behind a player is compared with their peers, in terms of current skill total
    - Only players belonging to active clubs are considered
  - **Energy Warning**: if a player will be below this level of energy for their next match, you will be notified prior to them being trained
- **Extra Training**: extra train players:
  - Min potentials
  - Min peer advantage
  - Energy Warning
  - **Max Exp**: Will not extra train players of this EXP total and above 
    - (e.g if set to 200, players with exp >=200 will not be extra trained) 
    
When you have finished with preferences, you can run the program
(Note these preferences can be modified again at any time from the menu.)
    
## Running Program
That's it. You can run the program and no more input from you is needed.

The first time you run the program, some data will be retrieved from best11.
This may take a few minutes.
However this data retrieval process will not happen every time you launch the program. 
For example, the active managers data is only retrieved on a weekly basis
