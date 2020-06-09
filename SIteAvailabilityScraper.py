import urllib.request
import re
import math
from datetime import date, timedelta, datetime
from bs4 import BeautifulSoup, Tag


# TODO: Add in pagination logic so we can get a large range of dates of availability for doing operations such as "any weekend in the next month". We'll probably have to store dates as actual dates, using the CST timezone as our base, so we can use libraries to get stuff such as what day of the week it is, so we can do "weekend" operations


class SiteAvailabilityScraper:
    DATE_FORMAT = '%m/%d/%Y'

    def __init__(self, park_id, start_date, end_date):
        """
        start_date and end_date can only be 14 days apart. If the end date is more than 14 days past the start date, it
        will just show you the 14 days after the start_date. Really the end date does nothing.

        :param park_id: integer of the park id. Find this by going on the page and viewing the calendar search for the park you want
        :param start_date: string in form "mm/dd/yyyy" (month and day must be zero-padded)
        :param end_date: string in form "mm/dd/yyyy" (month and day must be zero-padded)
        """
        self.park_id = park_id

        self.start_date = datetime.strptime(start_date, self.DATE_FORMAT).date()
        self.end_date = datetime.strptime(end_date, self.DATE_FORMAT).date()

        if (self.end_date - self.start_date).days < 1:
            raise ValueError("Your end date needs to be at least one day past your start date")

    @staticmethod
    def __generate_url(park_id, start_date, end_date):
        return "http://texas.reserveworld.com/GeneralAvailabilityCalendar.aspx?campId=" \
               + park_id + "&arrivalDate=" + start_date.strftime(SiteAvailabilityScraper.DATE_FORMAT)\
               + "&DepartureDate=" + end_date.strftime(SiteAvailabilityScraper.DATE_FORMAT)

    def get_availability_list(self):
        def __load_site(url):
            page = urllib.request.urlopen(url)
            return BeautifulSoup(page, "html.parser")

        def __extract_header(td):
            anchor_tags = td.find("a")
            if anchor_tags is not None:
                return anchor_tags.string.strip()
            return td.string.strip()

        def __process_site_row(site_row):
            row = list(map(lambda x: x.string.strip(), site_row.find_all("td")))
            site_type = SiteType(row[0])
            for i in range(first_date_index, last_date_index + 1):
                site_type.add_availability(SiteDate(headers[i], row[i]))
            return site_type.name, site_type

        def __get_header_tag(soup):
            table = soup.find(id="ctl07_tblMain")
            return table.find("tr", "altCampArea")

        def __extract_headers_from_row(header_row):
            headers_html = header_row.find_all("td")
            return list(map(__extract_header, headers_html))

        def __get_indicies_of_date_range(headers):
            regex = '^\d{1,2}/\d{2}$'
            first_date_index = SiteAvailabilityHelper.get_index_of_first_match(headers, regex)
            last_date_index = SiteAvailabilityHelper.get_index_of_last_match(headers, regex)
            return first_date_index, last_date_index

        def __get_date_ranges():
            date_delta = self.end_date - self.start_date

            biweeks = date_delta.days / 14
            date_ranges = []
            if biweeks > 1:
                whole_biweeks = int(math.floor(biweeks))
                for i in range(0, whole_biweeks):
                    range_start = self.start_date + timedelta(14 * i)
                    date_ranges.append((range_start, range_start + timedelta(13)))
                remaining_days = date_delta.days % 14
                if remaining_days > 0:
                    range_start = self.start_date + timedelta(14 * whole_biweeks)
                    date_ranges.append((range_start, range_start + timedelta(remaining_days)))
            else:
                date_ranges.append((self.start_date, self.end_date))
            return date_ranges

        for date_range in __get_date_ranges():
            start_range, end_range = date_range

            current_soup = __load_site(self.__generate_url(self.park_id, start_range, end_range))
            header_row = __get_header_tag(current_soup)
            headers = __extract_headers_from_row(header_row)
            first_date_index, last_date_index = __get_indicies_of_date_range(headers)

            availability_list = list(map(__process_site_row, filter(lambda x: type(x) is Tag,
                                                                    header_row.next_siblings)))

        return AvailabilityResults(availability_list)


class SiteAvailabilityHelper:
    @staticmethod
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

    @staticmethod
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


# TODO: Add in a SiteRule object that will take the rule, and the value, and store that as a map in the SiteType object
class SiteType:
    def __init__(self, site_name):
        self.name = site_name
        self.site_availability = dict()

    def add_availability(self, site_date):
        self.site_availability[site_date.date] = site_date

    def get_availability(self):
        return self.site_availability

class SiteDate:
    def __init__(self, date, num_available):
        self.date = date
        self.num_available = num_available


class DateAvailability:
    def __init__(self, date):
        self.total_available = 0
        self.date = date
        self._site_availability = dict()

    def add_site(self, site_name, num_free_sites):
        self._site_availability[site_name] = num_free_sites
        self.total_available += int(num_free_sites)


class AvailabilityResults:
    def __init__(self, site_types):
        self._site_types_list = site_types
        self._site_availability = None
        self._date_availability = None

    @property
    def site_types(self):
        return list(site_availability.keys())

    @property
    def site_availability(self):
        if self._site_availability is None:
            self._site_availability = dict()
            for site_type in self._site_types_list:
                self._site_availability[site_type[0]] = site_type[1]

        return self._site_availability

    @property
    def date_availability(self):
        if self._date_availability is None:
            self._date_availability = dict()
            for site_name, site_type in self._site_types_list:
                for availability_date, site_date in site_type.site_availability.items():
                    if availability_date not in self._date_availability:
                        self._date_availability[availability_date] = DateAvailability(availability_date)
                    self._date_availability[availability_date].add_site(site_name, site_date.num_available)
        return self._date_availability


# This example is for Enchanted Rock State Natural Area
scraper = SiteAvailabilityScraper("79", "03/02/2018", "03/05/2018")
availability_list = scraper.get_availability_list()
site_availability = availability_list.site_availability
overflow_sites = site_availability['OVERFLOW SITES']
# Need to modify this to take in a date object
march_second_availability = overflow_sites.get_availability()['03/02']

date_availability = availability_list.date_availability
