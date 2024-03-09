import json
import string
import requests
from bs4 import BeautifulSoup


class PageAlphabet:
    cyrillic_str = 'АБВГДЕЁЖЗИКЛМНОПРСТУФХЦЧШЩЭЮЯ'
    latin_str = string.ascii_uppercase
    local_data_on_february_2024 = {'7': [0],
                                   'A': [0],
                                   'E': [0],
                                   'F': [0],
                                   'N': [0],
                                   'Ё': [12],
                                   'А': [0, 1],
                                   'Б': [1, 2, 3, 4, 5],
                                   'В': [5, 6, 7],
                                   'Г': [7, 8, 9, 10],
                                   'Д': [10, 11, 12],
                                   'Е': [12],
                                   'Ж': [12],
                                   'З': [12, 13],
                                   'И': [13, 14],
                                   'К': [16, 17, 18, 19, 20, 21, 22, 23, 24],
                                   'Л': [24, 25, 26],
                                   'М': [26, 27, 28, 29, 30, 31, 32, 33, 34],
                                   'Н': [34, 35],
                                   'О': [35, 36, 37, 38],
                                   'П': [38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49],
                                   'Р': [49, 50, 51, 52],
                                   'С': [52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68],
                                   'Т': [68, 69, 70, 71, 72, 73],
                                   'У': [73],
                                   'Ф': [73, 74],
                                   'Х': [74, 75, 76, 77],
                                   'Ц': [77],
                                   'Ч': [77, 78, 79],
                                   'Ш': [79, 80, 81],
                                   'Щ': [81, 82],
                                   'Э': [82],
                                   'Ю': [82],
                                   'Я': [82]}


    @staticmethod
    def to_ranges(result: dict):
        result_ranges = {}
        for letter, pages in result.items():
            if len(pages) > 1:
                result_ranges[letter] = range(pages[0], pages[-1] + 1)
            else:
                result_ranges[letter] = range(pages[0], pages[0] + 1)
        return result_ranges

    def get_ranges(self, letter):
        # pages = self.get_pages()
        pages = self.local_data_on_february_2024
        return self.to_ranges(pages)[letter]


class Parser:
    CALORIZATOR_URL = "https://calorizator.ru/product/all"

    def __init__(self):
        self.page_amount = self.get_calorizator_pages_amount()

    def search_products(self, product_name: str):
        product_name_T = product_name.title()[0]
        alphabet = PageAlphabet()
        matches = {}
        for page_number in alphabet.get_ranges(product_name_T):
            content = self.get_calorizator_page(page_number)
            data = self.parse_calorizator_page(content)
            for product in data:
                if product_name.lower() in product.lower():
                    matches[product] = {"data": data[product], "page_number": page_number}
                else:

                    pass
        return matches

    @staticmethod
    def get_main_content(response: requests.Response):
        """ Function that gets <div id='main-content'>...</div> from the response. """
        soup = BeautifulSoup(response.content, 'html.parser')

        return soup.find("div", {"id": "main-content"})

    def get_calorizator_pages_amount(self) -> int:
        """ Returns the amount of pages on the calorizator site. """
        response = requests.get(self.CALORIZATOR_URL)

        if response.status_code != 200:
            raise Exception("Error while getting calorizator pages amount: {}".format(response.status_code))

        main_content = self.get_main_content(response)

        pager_last = main_content.find("li", {"class": "pager-last"})

        return int(pager_last.string)

    def get_calorizator_page(self, page_idx: int) -> requests.Response:
        """ Function to get the page from calorizator site. """
        response = requests.get(self.CALORIZATOR_URL, {"page": page_idx})

        if response.status_code != 200:
            raise Exception(
                "Error while getting calorizator page {}: {}".format(page_idx, response.status_code))

        return response

    @staticmethod
    def parse_float(data: str) -> float:
        """ Parses float from string. If parsing failed, returns 0.0 """
        try:
            return float(data.strip())
        except ValueError:
            return 0.0

    def parse_calorizator_page(self, page: requests.Response) -> dict[str, dict[str, float]]:
        """ Parses the calorizator page and extracts the calories data. """
        main_content = self.get_main_content(page)

        main_table = None

        for table in main_content.find_all("table"):
            try:
                # Find the first 'tr' entry in 'thead'.
                entries = table.thead.find("tr").find_all("th")[2:]
                # Entries list is expected to be like <li><a>NAME</a></li>.
                entries_names = list(map(lambda x: x.a.string, entries))

                # Check if th entries are expected ones.
                expected = ["Бел, г", "Жир, г", "Угл, г", "Кал, ккал"]
                if entries_names == expected:
                    # We found table that we need.
                    main_table = table
                    break
            except AttributeError:
                # If attribute error happened, it's not the table we're looking for.
                pass

        if not main_table:
            raise Exception("Not found main table on page {}".format(page))

        result = {}
        for entry in main_table.find("tbody").find_all("tr"):
            columns = entry.find_all("td")

            name = columns[1].a.string.strip()
            parsed_entry = {
                "protein": self.parse_float(columns[2].string),
                "fat": self.parse_float(columns[3].string),
                "carbohydrates": self.parse_float(columns[4].string),
                "calories": self.parse_float(columns[5].string),
            }

            result[name] = parsed_entry

        return result

    def to_json_file(self, page_number=None, all_pages=True):
        if page_number is not None:
            all_pages = False
            print(f"Writing page {page_number}")
            with open(f"calorizator_page_{page_number}.json", "w", encoding="utf-8") as f:
                json.dump(self.parse_calorizator_page(self.get_calorizator_page(page_number)), f,
                          ensure_ascii=False, indent=4)

        if all_pages:
            # create json file
            open(f"calorizator.json", "w", encoding="utf-8")
            # append to json file
            temp = {}

            for page in range(0, self.page_amount):
                temp.update(self.parse_calorizator_page(self.get_calorizator_page(page)))

            with open(f"calorizator.json", "a", encoding="utf-8") as f:
                json.dump(temp, f, ensure_ascii=False, indent=4)


