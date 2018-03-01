import urllib.request
import re
from bs4 import BeautifulSoup, Tag

# TODO: Add in pagination logic so we can get a large range of dates of availability for doing operations such as "any weekend in the next month". We'll probably have to store dates as actual dates, using the CST timezone as our base, so we can use libraries to get stuff such as what day of the week it is, so we can do "weekend" operations

class Scraper:
    def __init__(self, park_id, start_date, end_date):
        """
        start_date and end_date can only be 14 days apart. If the end date is more than 14 days past the start date, it
        will just show you the 14 days after the start_date. Really the end date does nothing.

        :param park_id: integer of the park id. Find this by going on the page and viewing the calendar search for the park you want
        :param start_date: string in form "(m)m/(d)d/yyyy
        :param end_date: string in form "(m)m/(d)d/yyyy
        """
        self.park_id = park_id
        self.start_date = start_date
        self.end_date = end_date
        self.url = "http://texas.reserveworld.com/GeneralAvailabilityCalendar.aspx?campId="\
                   + park_id + "&arrivalDate=" + start_date +"&DepartureDate=" + end_date

    def load_site(self):
        page = urllib.request.urlopen(self.url)
        self.soup = BeautifulSoup(page, "html.parser")


# TODO: Add in a SiteRule object that will take the rule, and the value, and store that as a map in the SiteType object
class SiteType:
    site_availability = { }

    def __init__(self, site_name):
        self.name = site_name

    def add_availability(self, site_date):
        self.site_availability[site_date.date] = site_date


class SiteDate:
    def __init__(self, date, num_available):
        self.date = date
        self.num_available = num_available


def extract_header(td):
    anchor_tags = td.find("a")
    if anchor_tags is not None:
        return anchor_tags.string.strip()
    return td.string.strip()


def get_index_of_first_match(lis, regex):
    """
Finds the the index of the first string in a list of strings that matches the provided regex string
    :param lis: list of strings
    :param regex: regular expression to match to
    :return: None if there was no matches. Int of index of the last match if there was a match
    """
    for i in range(0, len(lis)):
        if re.search(regex, lis[i]):
            return i
    return None


def get_index_of_last_match(lis, regex):
    """
Finds the the index of the last string in a list of strings that matches the provided regex string
    :param lis: list of strings
    :param regex: regular expression to match to
    :return: None if there was no matches. Int of index of the last match if there was a match
    """
    index_to_return = None
    for i in range(0, len(lis)):
        if re.search(regex, lis[i]):
            index_to_return = i
    return index_to_return


scraper = Scraper("79", "3/2/2018", "3/5/2018")
scraper.load_site()

table = scraper.soup.find(id="ctl07_tblMain")
headerRow = table.find("tr", "altCampArea")
headersHtml = headerRow.find_all("td")
headers = list(map(extract_header, headersHtml))

regex = '^\d{1,2}/\d{2}$'
first_date_index = get_index_of_first_match(headers, regex)
last_date_index = get_index_of_last_match(headers, regex)
dates = headers[first_date_index: last_date_index]

next_siblings = headerRow.next_siblings

site_type_list = []


def process_site(site_row):
    row = list(map(lambda x: x.string.strip(), site_row.find_all("td")))
    site_type = SiteType(row[0])
    for i in range(first_date_index, last_date_index + 1):
        site_type.add_availability(SiteDate(headers[i], row[i]))
    return site_type


availability_list = list(map(process_site, filter(lambda x: type(x) is Tag, next_siblings)))


