from bs4 import BeautifulSoup
import mysql.connector
import time
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
    database = "prod_proplist"
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
    currenttime = time.time()
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

    # Get any existing property record
    cursor = db.cursor()
    query = "SELECT * FROM propertylist_johnsonville WHERE addr = %s AND suburb = %s AND region = %s AND city = %s"
    val = (address, suburb, region, city)
    cursor.execute(query, val)
    propertyrecord = cursor.fetchall()
    cursor.close()

    # If the property record doesn't exist
    if len(propertyrecord) == 0:
        # Create the new property record
        cursor = db.cursor()
        query = "INSERT INTO propertylist_johnsonville SET addr = %s, suburb = %s, region = %s, city = %s, price = %s, active = 1"
        val = (address, suburb, region, city, price)
        cursor.execute(query, val)
        db.commit()
        cursor.close()
        # Create the new property record ID
        cursor = db.cursor()
        query = "SELECT * FROM propertylist_johnsonville WHERE addr = %s AND suburb = %s AND region = %s AND city = %s"
        val = (address, suburb, region, city)
        cursor.execute(query, val)
        newrecord = cursor.fetchall()
        cursor.close()
        # Create the new active listing record
        cursor = db.cursor()
        query = "INSERT INTO active_listings_johnsonville SET propid = %s, price = %s, link = %s, lastscan = %s"
        val = (newrecord[0][0], price, link, currenttime)
        cursor.execute(query, val)
        db.commit()
        cursor.close()

    # If the property is known
    elif len(propertyrecord) > 0:

        # Set the property to active
        if propertyrecord[0][6] == 0:
            # Only update the last scan time
            cursor = db.cursor()
            query = "UPDATE propertylist_johnsonville SET active = 1 WHERE id = %s"
            val = (propertyrecord[0][0],)
            cursor.execute(query, val)
            db.commit()
            cursor.close()

        # Get the active listing (if there is one)
        cursor = db.cursor()
        query = "SELECT * FROM active_listings_johnsonville WHERE propid = %s"
        val = (propertyrecord[0][0],)
        cursor.execute(query, val)
        activerecord = cursor.fetchall()
        cursor.close()

        # If there is an active listing
        if len(activerecord) > 0:

            # If this listing is the same as the active listing
            if activerecord[0][2] == price and activerecord[0][3] == link:
                # Only update the last scan time
                cursor = db.cursor()
                query = "UPDATE active_listings_johnsonville SET lastscan = %s WHERE id = %s"
                val = (currenttime, activerecord[0][0])
                cursor.execute(query, val)
                db.commit()
                cursor.close()

            # If this is a new listing
            else:
                # Create the new active listing record
                cursor = db.cursor()
                query = "INSERT INTO active_listings_johnsonville SET propid = %s, price = %s, link = %s, lastscan = %s"
                val = (activerecord[0][1], price, link, currenttime)
                cursor.execute(query, val)
                db.commit()
                cursor.close()
                # Move the current active into the prior record table
                cursor = db.cursor()
                query = "INSERT INTO prior_listings_johnsonville SET propid = %s, price = %s, link = %s, timeadded = %s"
                val = (activerecord[0][1], price, link, currenttime)
                cursor.execute(query, val)
                db.commit()
                cursor.close()
                # Delete the old one active one
                cursor = db.cursor()
                query = "DELETE FROM active_listings_johnsonville WHERE id = %s"
                val = (activerecord[0][0],)
                cursor.execute(query, val)
                db.commit()
                cursor.close()

        # If there is no active listing
        elif len(activerecord) == 0:
            # Create the new active listing record
            cursor = db.cursor()
            query = "INSERT INTO active_listings_johnsonville SET propid = %s, price = %s, link = %s, lastscan = %s"
            val = (propertyrecord[0][1], price, link, currenttime)
            cursor.execute(query, val)
            db.commit()
            cursor.close()

driver.quit()
db.close()

