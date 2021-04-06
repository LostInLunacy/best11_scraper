"""
    Get detailed information about the user's finance data
"""

# Imports
from collections import Counter
import re

# Local imports
from spider import Best11
from session import make_soup

class Finances(Best11):

    finance_subpage = 'finante.php'
    entries_per_page = 15

    def __init__(self):
        super().__init__()
        
        self.total_pages, self.entries_on_last_page = self.__get_last_page_info()

        print(self.entries_on_last_page)

    def __call__(self, newest_page=1, oldest_page=False, reverse=True):
        """
        Scrapes through finance pages
        Returns finance information

        r-type: ?
        """
        # Calculate oldest page to scrape from
        if not oldest_page: 
            oldest_page = self.total_pages
        else:
            oldest_page = min(oldest_page, self.total_pages)
        
        if reverse:
            return [self.get_page(i, reverse=True) for i in range(newest_page, oldest_page+1)]
        return [self.get_page(i) for i in range(oldest_page, newest_page-1, -1)]

    def __get_entry_start(self, page_num):
        """ 
        Find the starting_entry_id on a given page
        For example:
        If there are 4 pages total and 2 entries on the last page
        Then page 2 would start from an id of 18 (1 + 15 + 2)

        r-type: int
        """
        starting_id = 1
        if page_num == self.total_pages: return starting_id
        return starting_id + (self.total_pages - 1 - page_num) * 15 + self.entries_on_last_page

    def __get_entry(self, entry, entry_id):
        """
        Get an individual entry on a page of the finance table
        (e.g. club sales 5.000 C)
        Used by the self.get_page() func
        
        r-type: dict
        """
        # Get the £ amount of each entry
        amount = entry.find_all('td')[0].text 
        # Convert to valid number
        amount = self.get_value_from_string(amount)

        # What is the type of entry? (e.g. club sales)
        area = entry.find_all('td')[1].get_text().strip()[:-1]

        # Print data whilst iterating through
        print(f'{amount:16.3f} ({area}) [ID: {entry_id}]')

        return {
            'area': area,
            'amount': amount,
            'entry_id': entry_id
        }

    def get_page(self, page_num, reverse=False):
        if page_num not in range(1, self.total_pages+1):
            raise Exception(f"Page num {page_num} outside pages range")

        ## Get the starting entry id
        entries_num = self.entries_per_page if page_num != self.total_pages else self.entries_on_last_page
        entry_id = self.__get_entry_start(page_num)

        print("starting entry id", entry_id)

        ## Make request to page
        request = self.session.request(
            "GET",
            suburl=self.finance_subpage,
            params={'nr_pag': str(page_num)} # Arbitrary big number. Because we just want to go the last page
        )
        soup = make_soup(request)
        finance_table = soup.find_all('table', attrs={'width':300})[1].find_all('tr')[:-1]

        page_entries = [self.__get_entry(entry=finance_table.pop(), entry_id=entry_id+i) for i in range(0, entries_num)]
        
        if reverse: page_entries.reverse()
        return page_entries

    def __get_last_page_info(self):
        request = self.session.request(
            "GET",
            suburl=self.finance_subpage,
            params={'nr_pag': str(10**5)} # Arbitrary big number. Because we just want to go the last page
        )
        soup = make_soup(request)
        finance_table = soup.find_all('table', attrs={'width':300})[1]
        
        # Get page num
        page_back = finance_table.find('a', attrs={'href': re.compile(r"finante.php\?nr_pag=(\d+)$")}).get('href')
        page_num = int(re.findall(r"\d+$", page_back)[0]) + 1

        # Get num entries on last page
        last_page_entries = len(finance_table.find_all('tr'))-1

        return page_num, last_page_entries




if __name__ == "__main__":
    f = Finances()







    # def get_page(self, page_num):

    #     def __get_entry_data(self, entry):

    #         # Get the £ amount of each entry
    #         amount = entry.find_all('td')[0].text 
    #         # Convert to valid number
    #         amount = self.get_value_from_string(amount)

    #         # What is the type of entry? (e.g. club sales)
    #         area = entry.find_all('td')[1].get_text().strip()[:-1]

    #         # Print data whilst iterating through
    #         print(f'{amount:16.3f} ({area}) [ID: {entry_id}]')

    #         # Get entry_id


    #         return {
    #             'area': area,
    #             'amount': amount,
    #             'entry_id': entry_id
    #         }



    #     # Make request to page of finances
    #     request = self.session.request(
    #         "GET",
    #         suburl=self.finance_subpage,
    #         params={'nr_pag': str(page_num)}
    #     )
    #     soup = make_soup(request)

    #     # Locate the finance table
    #     finance_table = soup.find_all('table', attrs={'width':300})[1].find_all('tr')
    #     page_entries = [self.__get_entry_data(i) for i in finance_table]

        


    





        

        


























    # def get_finance_data(self):
        
    #     season = self.current_season
        
    # def get_finance_page_data(self, page_num):
        
    #     # Make request to page of finances
    #     request = self.session.request(
    #         "GET",
    #         suburl=self.finance_subpage,
    #         params={'nr_pag': str(page_num)}
    #     )
    #     soup = make_soup(request)

    #     # Locate the finance table
    #     finance_table = soup.find_all('table', attrs={'width':300})[1].find_all('tr')




    # def get_entry(self, entry):

    #     # Get the £ amount of each entry
    #     raw_amount = entry.find_all('td')[0].text 
    #     # Convert to valid number
    #     amount = self.get_value_from_string(raw_amount)

    #     # What is the type of entry? (e.g. club sales)
    #     area = entry.find_all('td')[1].get_text().strip()[:-1]







