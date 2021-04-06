"""
    Automation functions
"""

# Imports
import re
import random
from time import sleep

# Local imports
from spider import Best11
from session import make_soup
from club import Club

USER_CLUB = Club(manager='user')

class Auto(Best11):

    suburl_facilities = 'facilitati.php'
    suburl_finances = 'finante.php'
    suburl_clubpage = 'club.php'

    suburl_youthcoach = 'antrenor_juniori.php?'
    suburl_sponsor = 'sponsor.php?'    

    def __init__(self):
        super().__init__()

    """
    *** --- Dailies --- ***
    """
    def get_daily_bonus(self, choice=1):
        """ Collects the daily (login) bonus. """
        if not choice in range(1,6):
            raise ValueError("Choice must be in inclusive range 1-5")
        
        self.session.request(
            "GET",
            suburl='bonus_zilnic.php?',
            params={'cadou': choice}
        )

    def get_club_sales(self):
        """ Collects the club sales. """
        self.session.request(
            "GET",
            suburl='magazinul_clubului.php?',
            params={'pag': 'colectare'}
        )

    def get_bonus_from_partners(self, club_id=USER_CLUB.club_id):
        """ Collects the bonus from partners. """

        ## Get valid partner_ids
        response = self.session.request(
            "GET",
            suburl='bonus_parteneri.php?'
        )
        soup = make_soup(response)
        
        # Pattern to find bonus link
        pattern = r"get_bonus.php\?partener=(\d+)&"
        bonus_hrefs = [i.get('href') for i in soup.find_all('a', attrs={'href': re.compile(pattern)})]
        
        # Extract partner_ids from bonus_links
        # NOTE: redboy frequently changes these as websites go down, hence it's good to get up to date partner_ids
        valid_partner_ids = [int(re.findall(pattern, i)[0]) for i in bonus_hrefs]

        # Collect bonus for each partner_id
        get_bonus = lambda partner_id: self.session.request("GET", suburl='get_bonus.php?', params={'partener': partner_id, 'club':club_id})
        [get_bonus(partner) for partner in valid_partner_ids]   
        
    def __get_tp_from_slot(self, slot_num):
        response = self.session.request(
            "POST",
            'antrenor.php?',
            params={'pag': 'antrenament', 'slot': slot_num}
        )

        soup = make_soup(response)
        div_text = soup.find_all('div')[4].text
        value = float(re.findall(r"(\d?.\d{3}) TP", div_text)[0])

        # Fix values
        if value > 10 and value < 100: 
            raise ValueError("Unknown training point value")
        elif value <= 10:
            value *= 1000
        
        return int(value)

    def get_training_points(self, only_slot=None, max_tp=False):
        """ Collects training points. """
        # TODO not allow if training session already completed

        if max_tp and self.tp_balance > max_tp:
            print("Exceeded max set TP")

        current_techstaff = self.techstaff

        if not current_techstaff:
            raise Exception("Can't collect training points - no tech staff have been hired!")
        if only_slot and not current_techstaff.get(1):
            raise Exception(f"No coach hired in selected slot: {only_slot}")

        slots_to_train = [only_slot] if only_slot else (1,2)

        total_tp_earnt = 0
        for slot in slots_to_train:
            total_tp_earnt += self.__get_tp_from_slot(slot)

        return total_tp_earnt

    """
    *** --- Balances --- ***
    """
    @property
    def credits_balance(self):
        """
        Returns the user's credit balance

        r-type: int
        """
        response = self.session.request(
            "GET",
            suburl=self.suburl_clubpage
        )
        credits_balance_text = make_soup(response).find_all('table')[20].find_all('td')[1].text
        try:
            return self.get_value_from_string(credits_balance_text)
        except:
            raise Exception(f"Could not find credits balance in text:\n{credits_balance_text}")

    @property
    def tp_balance(self):
        """
        Returns the user's TP balance

        r-type: int
        """
        response = self.session.request(
            "GET",
            suburl=self.suburl_clubpage
        )
        tp_balance_text = make_soup(response).find_all('table')[22].find_all('td')[1].text
        try:
            return self.get_value_from_string(tp_balance_text)
        except:
            raise Exception(f"Could not find credits balance in text:\n{tp_balance_text}")
    
    """
    *** --- Youth Coaches --- ***
    """
    @property
    def youthcoach(self):

        response = self.session.request("GET", self.suburl_facilities)
        soup = make_soup(response)
        youth_coach_box = soup.find_all('table')[3].find_all('tr')[1]

        try:
            name = youth_coach_box.find('b').text
        except:
            # You do not have a youth coach
            return False

        link = youth_coach_box.find('a', attrs={'onmouseover': True})
        pattern = r"Salary: (\d{1}\.?\d{0,3}) C"
        salary = int(re.findall(pattern, link['onmouseover'])[0])

        pattern = r"stele/(\d{1,2})"
        star_ratings = tuple([int(re.findall(pattern, i['src'])[0])//2 for i in 
            soup.find_all('table')[4].find_all('tr')[1].find_all('img', attrs={'src': re.compile(r"imagini/stele/")})
            ])

        return {'name': name, 'salary': salary, 'ratings': star_ratings}

    def youthcoach_rename(self, first_name, last_name):
        """
        Renames your youth coach
        """
        if not (current_youthcoach := self.youthcoach):
            raise Exception("Cannot rename coach that doesn't exist!")
 
        self.youthcoach_hire(
            first_name=first_name, 
            last_name=last_name,
            salary=current_youthcoach['salary']*1000,
            signon=0,
            ratings=current_youthcoach['ratings'],
            replace=True
        )

    def youthcoach_fire(self):
        """ Fire your current youth coach. """

        # Make confirmation to fire youth coach
        self.session.request(
            "GET",
            suburl=self.suburl_youthcoach,
            params={'pag': 'concediaza', 'confirmare': 1}
        )

    def youthcoach_hire(self, first_name, last_name, salary=0, signon=0, ratings=(1,1,1,1), replace=False):
        """
        Hires a youth coach

        Params:
        - first_name (str)
        - last_name (str)
        - salary (int) 110.000 C -> 110
        - signon (int) 110.000 C -> 110
        - ratings (tuple of len 4, all values 1-5 inclusive)
            The star rating of the youth coach (e.g. 1-1-5-2)
        - replace (bool)
            If True and a current youth coach exists, they will be fired before new coach is hired.
            Otherwise if the youth coach exists but replace=False, method will return False.

        r-type: None
        """

        if not isinstance(ratings, tuple) or len(ratings)!=4 or not all([i in range(1,6) for i in ratings]):
            raise TypeError(f"Invalid ratings value: {ratings}")

        keepers, defenders, midfielders, strikers = [x*2 for x in ratings]

        # If you have a current youth coach, fire them
        if self.youthcoach:
            if not replace: return False
            self.youthcoach_fire()

        if salary != (legit_salary := self.__youthcoach_calculate_salary(ratings)):
            print(f"Salary should be {legit_salary}, not {salary}")

        # Generate coach to hire
        self.session.request(
            "POST", 
            suburl=self.suburl_youthcoach,
            params={'pag': 'semneaza'},
            data={
                'nume': last_name,
                'prenume': first_name,
                'P': keepers,
                'F': defenders,
                'M': midfielders,
                'A': strikers,
                'salariu': salary,
                'semnatura': signon,
                'submit': 'sign'
            }
        )

        # Confirm hire of coach
        self.session.request("GET", suburl=self.suburl_youthcoach, params={'pag': 'confirmare'})

    @staticmethod
    def __youthcoach_calculate_salary(ratings):
        """
        Determines and returns the salary a youth coach should have, given their ratings
        r-type: int.
        """
        salary = 0
        salary += 60 * ratings.count(5)
        salary += 30 * ratings.count(4)
        salary += 15 * ratings.count(3)
        salary += 10 * ratings.count(2)
        salary += 5 * ratings.count(1)
        return salary

    """
    *** --- Technical Staff --- ***
    """
    @property
    def techstaff(self):
        """
        Gets the current tech staff
        """

        def coach_stat_string_to_values(onmouseover):
            """
            Converts an onmouseover for a coach into level and salary
            popup('Level: 10/10 <br> Salary: 25.200 C','#f1f1f1') -> (10, 25.2)

            r-type: tuple (len 2)
            """
            stats = re.findall(pattern, onmouseover)[0]
            print(stats)
            return tuple([int(stats[0]), self.get_value_from_string(stats[1])])

        ## Go to the facilities page
        response = self.session.request("GET", suburl=self.suburl_facilities)
        techstaff_box = make_soup(response).find_all('table')[2].find_all('tr')[1]

        ## Get the slot numbers for which you have a coach
        occupied_slots = [int(x.get('href')[-1]) for x in techstaff_box.find_all('a', attrs={'href': re.compile(r"antrenor.php\?pag=concediaza&slot=\d$")})]
        
        ## Coach Stats
        # Get the onmouseover containing coach level and salary. (Yes, this is the only way to get it...)
        pattern = r"Level: (\d{1,2})\/10 <br> Salary: (\d{1,3}\.?\d{0,3} C)"
        coach_stats_strings = [i.get('onmouseover') for i in techstaff_box.find_all('a', attrs={'onmouseover': re.compile(pattern)})]
        if len(occupied_slots) != len(coach_stats_strings):
            raise Exception(f"Uneven number of coaches and coach stats program could scrape\n{occupied_slots}\n{coach_stats_strings}")
        # Use function within method to convert onmouseovers to readable format
        coach_stats = [coach_stat_string_to_values(s) for s in coach_stats_strings]

        ## Coach Names
        coach_names = [x.text for x in techstaff_box.find_all('b')]
        
        techstaff = {}
        while occupied_slots:
            slot_num = occupied_slots.pop(0)
            level, salary = coach_stats.pop(0)
            name = coach_names.pop(0)
            techstaff[slot_num] = {'name': name, 'level': level, 'salary': salary}

        return techstaff

    def techstaff_rename(self, slot, first_name, last_name):
        """
        Renames a technical staff member
        """
        if slot not in (1,2):
            raise ValueError("Slot must be either 1 or 2")

        current_techstaff = self.techstaff
        try:
            existing = current_techstaff[slot]
        except KeyError:
            raise Exception(f"Can't seem to find a coach to rename in slot {slot}!")
        else:
            self.techstaff_hire(
                slot=slot, 
                first_name=first_name, 
                last_name=last_name,
                level=existing['level'],
                salary=existing['salary']*1000,
                signon=0
            )

    def techstaff_fire(self, slot):
        """
        Fires a youth coach

        Params:
        - Slot (int of value 1 or 2)
            The slot number of the coach

        r-type: None
        """

        if slot not in (1,2):
            raise Exception("Slot must be either 1 or 2")
        
        self.session.request(
            "GET",
            suburl='antrenor.php?',
            params={'pag': 'concediaza', 'slot': slot, 'confirmare': 1}
        )

    def techstaff_hire(self, slot, first_name, last_name, level=1, salary=0, signon=0):
        """
        Hires a tech staff member
        """
        if slot not in (1,2):
            raise ValueError("Slot must be either 1 or 2")
        elif level not in range(1,11):
            raise ValueError("Level must be in range 1-10 inclusive")

        # Generate coach to hire
        response = self.session.request(
            "POST",
            suburl='confirma_antrenor.php',
            data={
                'slot': slot,
                'nivel': level,
                'prenume': first_name,
                'nume': last_name,
                'salariu': salary,
                'semnatura': signon,
                'submit': 'sign'
            }
        )

        # Confirm hire of coach
        self.session.request("GET", suburl='antrenor_nou.php')

    """
    *** --- Psychologists --- ***
    """
    @property
    def psych(self):
        """
        Get the current hired psychologist if one exists
        Otherwise returns False.
        """
        
        response = self.session.request(
            "GET",
            suburl=self.suburl_facilities
        )
        soup = make_soup(response)

        psych_box = soup.find_all('table')[9].find_all('tr')[1]

        if psych_box.find_all('input', attrs={'value': 'Hire psychologist'}):
            # No psychologist is hired at the moment
            return False

        name = psych_box.find('b').text
        
        link = psych_box.find('a', attrs={'onmouseover': True})
        pattern = r"Level: (\d{1})/5 <br> Consultation: (\d{1,3}\.\d{3}) C"
        level, consultation = re.findall(pattern, link['onmouseover'])[0]

        level = int(level)
        consultation = self.get_value_from_string(consultation)

        return {'name': name, 'level': level, 'consultation': consultation}

    def psych_rename(self, first_name, last_name):
        """
        Rename a psychologist
        """

        if not (current_psychologist := self.psych):
            raise Exception("Cannot rename psychologist that doesn't exist!")

        self.psych_hire(
            first_name=first_name, 
            last_name=last_name,
            level=current_psychologist['level'],
            salary=current_psychologist['consultation']*1000,
            signon=0
        )

    def psych_fire(self):
        """
        Fire a psychologist if one exists
        """
        if not self.psych:
            raise Exception("There is no psychologist to fire!")

        self.session.request(
            "GET",
            suburl='psiholog.php?',
            params={'pag': 'concediaza', 'confirmare': 1}
        )
        pass

    def psych_hire(self, first_name, last_name, salary=0, signon=0, level=1):
        
        # Generate coach to hire
        self.session.request(
            "POST",
            suburl='confirma_psiholog.php',
            data={
                'nivel': level,
                'prenume': first_name,
                'nume': last_name,
                'salariu': salary,
                'semnatura': signon
            }
        )

        # Confirm hire of coach
        self.session.request("GET", suburl='psiholog_nou.php')

    """
    *** --- Sponsorship --- ***
    """
    @property
    def sponsors(self):

        def sponsor_stat_string_to_values(onmouseover):
            """
            Converts an onmouseover for a sponsor into a payemnt, victory and draw 
            (the last two referring to the win/draw bonuses)

            popup('<b>Payment:</b><br>22.000 C / match<br><b>Win Bonus:</b><br>7.220 C<br><b>Draw Bonus:</b><br>2.900 C','#f1f1f1')
            -> (22, 7.22, 2.9)

            r-type: tuple (len 3)
            """
            stats = re.findall(pattern, onmouseover)[0]
            return tuple([self.get_value_from_string(i) for i in stats])

        ## Go to the finances page
        response = self.session.request("GET", suburl=self.suburl_finances)
        sponsors_box = make_soup(response).find_all('table')[4]

        ## Get the slot numbers for which you have a sponsor
        pattern = r"sponsor.php\?slot=(\d)&pag=anulare$"
        occupied_slots = [int(re.findall(pattern, x.get('href'))[0]) for x in sponsors_box.find_all('a', attrs={'href': re.compile(pattern)})]

        ## Sponsor stats
        pattern = r"popup\('<b>Payment:</b><br>(\d{1,2}\.\d{1,3} C) / match<br><b>Win Bonus:</b><br>(\d{1,2}\.\d{1,3} C)<br><b>Draw Bonus:</b><br>(\d{1,2}\.\d{1,3} C)','#f1f1f1'\)"
        sponsor_stats_strings = [i.get('onmouseover') for i in sponsors_box.find_all('a', attrs={'onmouseover': re.compile(pattern)})]
        if len(occupied_slots) != len(sponsor_stats_strings):
            raise Exception("Uneven number of sponsors and sponsors' stats program could scrape")
        # Use function within method to convert onmouseover to readable format
        sponsor_stats = [sponsor_stat_string_to_values(s) for s in sponsor_stats_strings]

        ## Sponsor Names
        pattern = r"imagini\/sponsori\/(\w+)\.gif"
        sponsor_names = [re.findall(pattern, i.get('src')) for i in sponsors_box.find_all('img', attrs={'src': re.compile(pattern)})]

        sponsors = {}
        while occupied_slots:
            slot_num = occupied_slots.pop(0)
            payment, victory_bonus, draw_bonus = sponsor_stats.pop(0)
            name = sponsor_names.pop(0)
            sponsors[slot_num] = {'name': name, 'payment': payment, 'victory': victory_bonus, 'draw': draw_bonus}

        return sponsors

    def sponsor_fire(self, slot):
        self.session.request(
            "GET",
            suburl=self.suburl_sponsor,
            params={'slot': slot, 'pag': 'anulare'}
        )

    def sponsor_hire(self, slot, sponsor=None, min_payment=21.9, min_victory=7.3, min_draw=3):
        # TODO: If not sponsor, generate random one
        if self.sponsors.get(slot):
            self.sponsor_fire(slot)

        if not sponsor:
            sponsor = random.choice(self.sponsors_options_list)
        elif sponsor not in self.sponsors_options_list:
            raise Exception(f"Invalid sponsor: {sponsor}. Please select from the list.")

        def generate_sponsor_contract(slot, sponsor):
            response = self.session.request(
                "GET",
                suburl=self.suburl_sponsor,
                params={'slot': slot, 'pag': 'oferta', 'sponsor': sponsor}
            )
            soup = make_soup(response)
            contract_row = [i.text for i in soup.find('table').find_all('tr')[1].find_all('td')[1:]]
            contract_row[0] = contract_row[0].split('/match')[0]
            assert len(contract_row) == 3

            payment, victory, draw = [self.get_value_from_string(i) for i in contract_row]
            if payment < min_payment:
                return False
            if victory < min_victory:
                print(f"victory: {victory} too low")
                return False
            if draw < min_draw:
                print(f"draw: {draw} too low")
                return False
            
            # Confirm contract
            self.session.request(
                "GET",
                suburl=self.suburl_sponsor,
                params={'slot': slot, 'sponsor': sponsor, 'pag': 'confirmare'}
            )

            # Return contract so it can be printed to console when made
            contract = {'payment': payment, 'victory': victory, 'draw': draw}
            return contract

        attempts = 0
        while True:
            attempts += 1
            if(sponsor_contract := generate_sponsor_contract(slot=slot, sponsor=sponsor)):
                print(f"Succeeded in {attempts} attempts")
                return sponsor_contract

            if attempts % 10 == 0:
                sleep(2)

    @property
    def sponsors_options_list(self):
        sponsors = self.sponsors
        slot = 1
        
        if len(sponsors) == 2:
            raise Exception("Cannot get sponsors list if both sponsor slots are full")
        elif sponsors.get(1):
            slot = 2

        response = self.session.request(
            "GET",
            suburl='sponsor.php?',
            params={'slot': slot}
        )
        table = make_soup(response)

        pattern = r"sponsori\/(\w+)\.gif"
        sponsor_srcs = [i.get('src') for i in table.find_all('img', attrs={'src': re.compile(pattern)})]
        return [re.findall(pattern, i)[0] for i in sponsor_srcs]

    """
    *** --- Medical Department --- ***
    """
    @property
    def medical_allowance(self):
        """
        Get the medical allowance level (1-5 inclusive)
        r-type: int
        """
        response = self.session.request("GET", suburl=self.suburl_facilities)
        soup = make_soup(response)
        medical_box = soup.find_all('table')[8]

        selected = medical_box.find('option', attrs={'selected':True})
        return int(selected.get('value'))

    @medical_allowance.setter
    def medical_department_allowance(self, level=1):
        """
        1: 10.000 C
        2: 25.000 C
        3: 50.000 C
        4: 75.000 C
        5: 100.000 C
        """
        self.session.request(
            "POST",
            suburl='investitie_cm.php',
            data={'cabinet_medical': level}
        )


if __name__ == "__main__":
    a = Auto()
