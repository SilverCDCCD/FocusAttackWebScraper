from datetime import date

from bs4 import BeautifulSoup
import csv
import os, os.path
import requests
import shutil

global old_prices, new_prices, prices_csv, reader

csv_path = './prices.csv'
site_page = 'https://focusattack.com/{2}/popular-brands/{0}/?page={1}'
brands = {"pushbuttons": ['Sanwa', 'Seimitsu', 'Crown/Samducksa', 'Industrias Lorenzo', 'Suzo Happ'],
		  "joysticks": ["Sanwa", "Seimitsu", "Hori", "Crown/Samducksa", "Taeyoung", "IST", "Industrias Lorenzo", "Suzo Happ", "Arcade Sticks Indonesia", "Kowal", "Phreakmods"],
		  "spare-parts-tools": ["Industrias Lorenzo", "Sanwa", "Seimitsu", "Crown"],
		  "hardware-pcb": ["Brook", "GP2040-CE"],
		  "electrical": ["Neutrik", "Philmore", "Sanwa"],
		  "fightsticks": ["BNB Fightstick", "AllFightSticks"]}


def compare() -> None:
	pricing_updates = {}
	new_products = []
	dropped_products = []

	for prod in new_prices.keys():
		try:
			if old_prices[prod] != new_prices[prod]:
				pricing_updates[prod] = [old_prices[prod], [new_prices[prod]]]
		# Product not found in old_products
		except KeyError:
			new_products.append(prod)

	for prod in old_prices.keys():
		try:
			new_prices[prod]
		except KeyError:
			dropped_products.append(prod)

	generate_report(pricing_updates, new_products, dropped_products)


def confirm_folders():
	if not os.path.exists("./old-prices"):
		os.mkdir("./old-prices")
	if not os.path.exists("./reports"):
		os.mkdir("./reports")


def generate_report(price_changes: dict, new: list, dropped: list) -> None:
	s: str = f"Report for {date.today().month}/{date.today().day}/{date.today().year}\n"

	# Show price changes
	s += "\nPrice Changes:"
	if len(price_changes.keys()) == 0:
		s += "\n\tNone"
	else:
		for product in price_changes.keys():
			old_price: float = price_changes[product][0]
			new_price: float = price_changes[product][1][0]
			s += f'\n\t{product}: ${old_price:.2f} -> ${new_price:.2f}'

	# Show new products
	s += "\n\nNew Products:"
	if len(new) == 0:
		s += '\n\tNone'
	else:
		for product in new:
			s += f'\n\t{product}'

	# Show dropped products
	s += "\n\nDropped products:"
	if len(dropped) == 0:
		s += '\n\tNone'
	else:
		for product in dropped:
			s += f'\n\t{product}'

	report_file = open(f'./reports/report_{date.today()}.txt', 'w')
	report_file.write(s)
	report_file.close()
	print('Report created')


def get_brand_url(brand: str) -> str:
	return brand.replace('/', '-').replace(' ', '-').lower()


def get_old_prices() -> None:
	global old_prices, prices_csv, reader
	old_prices = {}
	prices_csv = open(csv_path, 'r')
	reader = csv.DictReader(prices_csv)

	for result in reader:
		try:
			prod = result['ProductName']
			price = result['Price']
			old_prices[prod] = float(price)
		except ValueError:
			continue


def get_new_prices() -> None:
	global new_prices
	new_prices = {}
	for cat in brands.keys():
		retrieve_prices(cat)


def retrieve_prices(_category: str) -> None:
	_brands = brands[_category]
	
	if len(_brands) == 0:
		return
	
	for brand in _brands:
		page_no = 1
		while True:
			page = requests.get(site_page.format(get_brand_url(brand), page_no, _category))
			soup = BeautifulSoup(page.text, 'html.parser')
			products = soup.find_all('span', attrs={'class': 'ProductName'})
			prices = soup.find_all('span', attrs={'class': 'ProductPrice'})

			if len(products) < 1 or len(prices) < 1:
				break
			for prod, price in zip(products, prices):
				try:
					new_prices[prod.text] = float(price.text[1:])
				except ValueError:
					new_prices[prod.text] = float(price.span.text[1:])
			print(f"Retrieved {_category.replace('-', ' ').title()} prices for {brand} (Page {page_no})")
			page_no += 1


def rollback():
	try:
		# Find old price lists
		old_price_list = [f for f in os.listdir("old-prices")]
		report_list = [f for f in os.listdir("reports")]
	
		if len(old_price_list) < 1:
			raise FileNotFoundError
	
		# Replace existing price list
		shutil.copy(f"old-prices/{old_price_list[-2]}", "./prices.csv")
		
		# Delete unnecessary price lists
		os.remove(f"old-prices/{old_price_list[-1]}")
		os.remove(f"reports/{report_list[-1]}")
		print("Rollback completed")
	
	except FileNotFoundError:
		print("No records found")


def run():
	confirm_folders()
	
	get_old_prices()
	get_new_prices()

	compare()
	update_prices()

	prices_csv.close()


def update_prices():
	global new_prices
	s: str = 'ProductName,Price'
	for key, value in new_prices.items():
		s += f'\n{key},{value}'

	# Catalog old prices
	today = date.today()
	shutil.copy('./prices.csv', './old-prices')
	shutil.move('./old-prices/prices.csv', f'./old-prices/prices-{today.year}-{today.month:02}-{today.day:02}.csv')

	# Update new prices
	with open('./prices.csv', 'w', newline="") as file:
		file.write(s)
		print('Prices updated')


def main_menu():
	try:
		option = int(input("\nSelect operation.\n1: Run Scraper\n2: Rollback\n0: Exit "))
		match option:
			case 1:
				run()
				main_menu()
			case 2:
				rollback()
				main_menu()
			case 0:
				print("Web scraper terminated.")
			case _:
				raise TypeError
	except TypeError:
		print("Error! Enter a number from 0-2.")
		main_menu()


if __name__ == '__main__':
	main_menu()
