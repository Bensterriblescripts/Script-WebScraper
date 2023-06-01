from bs4 import BeautifulSoup
import mysql.connector
import time
import re
import os

from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options

# DB
sqluser = os.environ["MYSQL_USER"]
sqlpass = os.environ["MYSQL_PASS"]

db = mysql.connector.connect(
    host = "localhost",
    user = sqluser,
    password = sqlpass,
    database = "prod_proplistings"
)

# Uses the Edge webdriver
webdriver_service = Service('C:/Local/WebDriver/113.0.1774.57/msedgedriver.exe')
edge_options = Options()
edge_options.add_argument("--headless")  # Run Edge in headless mode, without opening a window
edge_options.add_argument("--log-level=3")  # Suppress console output
driver = webdriver.Edge(service=webdriver_service, options=edge_options)
url = "https://www.trademe.co.nz/a/property/residential/sale/wellington/wellington/johnsonville"
driver.get(url)
time.sleep(5)
html_content = driver.page_source

# Parse HTML by class, store all <a> tags in links[]
soup = BeautifulSoup(html_content, "html.parser")
class_name = "l-col l-col--has-flex-contents ng-star-inserted"
elements = soup.find_all(class_=class_name)
baselinks = []
for element in elements:
    a_tags = element.find_all("a")
    baselinks.extend(a_tags)

# Get the href, then remove the query string from the URL
pagelinks = []
for link in baselinks:
    pagelink = link.get("href")
    index = pagelink.find("?")
    slicedlink = pagelink[:index]
    proplink = url + slicedlink
    pagelinks.append(proplink)

# Loop through each property page
for link in pagelinks:
    print(link)
    driver.get(link)
    time.sleep(5)
    html_content = driver.page_source
    soup = BeautifulSoup(html_content, "html.parser")

    # Get the property address
    class_name = "tm-property-listing-body__location p-h3"
    htmllocation = soup.find(class_=class_name)
    location = htmllocation.get_text()
    print(location)
    locationsplit = location.split(", ")
    address = locationsplit[0]
    suburb = locationsplit[1]
    region = locationsplit[2]
    if len(locationsplit) > 3:
        city = locationsplit[3]
    else:
        city = ""

    # Get the property price
    propvalue = soup.select('[data-th="Value"]')
    htmlprice = [pv.text for pv in propvalue if pv.text.strip().startswith('$')]
    if htmlprice:
        price = htmlprice[0].strip("[]'")
        print(price)
    else:
        price = "Not Listed" 
        print("Price not listed")

    # Add to the scantable
    try:
        currenttime = time.time()
        cursor = db.cursor()
        query = "INSERT INTO scan_trademe_johnsonville SET addr = %s, suburb = %s, region = %s, city = %s, price = %s, link = %s, lastscan = %s"
        val = (address, suburb, region, city, price, link, currenttime)
        cursor.execute(query, val)
        db.commit()
        cursor.close()
    except Exception as e:
        print("Error:", e)


driver.quit()
db.close()

