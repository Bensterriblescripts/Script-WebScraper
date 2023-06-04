from bs4 import BeautifulSoup
import mysql.connector
import time
import os
from selenium import webdriver
from selenium.webdriver.edge.service import Service
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
# Query - SELECT
def getrecords(query, val):
    cursor = db.cursor()
    cursor.execute(query, val)
    records = cursor.fetchall()
    cursor.close()
    return records
# Query - UPDATE/INSERT/DELETE
def changerecords(query, val):
    cursor = db.cursor()
    cursor.execute(query, val)
    db.commit()
    cursor.close()
# Query - No variables
def fixrecords(query):
    cursor = db.cursor()
    cursor.execute(query)
    db.commit()
    cursor.close()

# TradeMe
scanregions = ['crofton+downs', 'johnsonville', 'khandallah', 'newlands', 'newtown', 'paparangi', 'raroa', 'rongotai', 'tawa']
for setregion in scanregions:
    site = "trademe"

    # Link changes on specific regions
    if "+" in setregion:
        fsetregion = setregion.replace('+', '-')
        baseurl = "https://www.trademe.co.nz/a/property/residential/sale/wellington/wellington/" + fsetregion
        setregion = setregion.replace('+', '')
    else:
        baseurl = "https://www.trademe.co.nz/a/property/residential/sale/wellington/wellington/" + setregion

    # Create the tables if required
    query = "CREATE TABLE IF NOT EXISTS propertylist_" + setregion + " (id INT AUTO_INCREMENT PRIMARY KEY, addr VARCHAR(255), suburb VARCHAR(45), region VARCHAR(45), city VARCHAR(45), price VARCHAR(255))"
    fixrecords(query)
    query = "CREATE TABLE IF NOT EXISTS active_listings_" + setregion + " (id INT AUTO_INCREMENT PRIMARY KEY, propid INT, price VARCHAR(45), link VARCHAR(255), site VARCHAR(45), lastscan INT)"
    fixrecords(query)
    query = "CREATE TABLE IF NOT EXISTS prior_listings_" + setregion + " (id INT AUTO_INCREMENT PRIMARY KEY, propid INT, price VARCHAR(45), link VARCHAR(255), site VARCHAR(45), timeadded INT)"
    fixrecords(query)

    # Uses the Edge webdriver
    webdriver_service = Service('C:/Local/WebDriver/113.0.1774.57/msedgedriver.exe')
    edge_options = Options()
    edge_options.add_argument("--headless")
    edge_options.add_argument("--log-level=3")
    driver = webdriver.Edge(service=webdriver_service, options=edge_options)
    driver.get(baseurl)
    time.sleep(5)
    html_content = driver.page_source

    # Parse HTML by class, store all the links
    soup = BeautifulSoup(html_content, "html.parser")
    tiles = "l-col l-col--has-flex-contents ng-star-inserted"
    elements = soup.find_all(class_=tiles)

    # Property links on current page
    baselinks = []
    for element in elements:
        a_tags = element.find_all("a")
        baselinks.extend(a_tags)
    pagelinks = []
    for link in baselinks:
        pagelink = link.get("href")
        index = pagelink.find("?")
        slicedlink = pagelink[:index]
        proplink = baseurl + slicedlink
        pagelinks.append(proplink)

    # Navigation page links
    pages = "o-pagination__nav-item ng-star-inserted"
    pageelements = soup.find_all(class_=pages)
    pagebaselinks = []
    for pageelement in pageelements:
        a_tags = pageelement.find_all("a")
        pagebaselinks.extend(a_tags)
    navigationlinks = []
    for navlinks in pagebaselinks:
        navlink = navlinks.get("href")
        navigationlinks.append(navlink)

    # Move onto the next page
    for navlinks in navigationlinks:
        navurl = baseurl + navlinks
        driver.get(navurl)
        time.sleep(5)
        html_content = driver.page_source
        soup = BeautifulSoup(html_content, "html.parser")
        tiles = "l-col l-col--has-flex-contents ng-star-inserted"
        elements = soup.find_all(class_=tiles)

        # Property links on current page
        for element in elements:
            a_tags = element.find_all("a")
            baselinks.extend(a_tags)
        for link in baselinks:
            pagelink = link.get("href")
            index = pagelink.find("?")
            slicedlink = pagelink[:index]
            proplink = baseurl + slicedlink
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
        query = "SELECT * FROM propertylist_" + setregion + " WHERE addr = %s AND suburb = %s AND region = %s AND city = %s"
        val = (address, suburb, region, city)
        propertyrecord = getrecords(query, val)

        # If the property record doesn't exist
        if len(propertyrecord) == 0:

            # Create the new property record
            query = "INSERT INTO propertylist_" + setregion + " SET addr = %s, suburb = %s, region = %s, city = %s, price = %s"
            val = (address, suburb, region, city, price)
            changerecords(query, val)

            # Get new property record ID
            query = "SELECT * FROM propertylist_" + setregion + " WHERE addr = %s AND suburb = %s AND region = %s AND city = %s"
            val = (address, suburb, region, city)
            newrecord = getrecords(query, val)

            # Create the new active listing record
            query = "INSERT INTO active_listings_" + setregion + " SET propid = %s, price = %s, link = %s, site = %s, lastscan = %s"
            val = (newrecord[0][0], price, link, site, currenttime)
            changerecords(query, val)

        # If the property is known
        elif len(propertyrecord) > 0:

            # Get the active listing (if there is one)
            query = "SELECT * FROM active_listings_" + setregion + " WHERE propid = %s AND site = %s"
            val = (propertyrecord[0][0], site)
            activerecord = getrecords(query, val)

            # If there is an active listing
            if len(activerecord) > 0:

                # Known listings
                if activerecord[0][2] == price:

                    # Only update the last scan time
                    query = "UPDATE active_listings_" + setregion + " SET lastscan = %s WHERE id = %s"
                    val = (currenttime, activerecord[0][0])
                    changerecords(query, val)

                # New listings
                else:
                    # Create the new active listing record
                    query = "INSERT INTO active_listings_" + setregion + " SET propid = %s, price = %s, link = %s, site = %s, lastscan = %s"
                    val = (activerecord[0][1], price, link, site, currenttime)
                    changerecords(query,val)

            # If there is no active listing
            elif len(activerecord) == 0:
                
                # Create the new active listing record
                query = "INSERT INTO active_listings_" + setregion + " SET propid = %s, price = %s, link = %s, site = %s, lastscan = %s"
                val = (propertyrecord[0][0], price, link, site, currenttime)
                changerecords(query, val)

    # Get existing listings older than 24 hours
    currenttime = time.time()
    query = "SELECT * FROM active_listings_" + setregion + " WHERE lastscan < %s"
    val = ((currenttime - 86400),)
    oldrecord = getrecords(query, val)
    if len(oldrecord) != 0:
        for record in oldrecord:

            # Move the current active into the prior record table
            query = "INSERT INTO prior_listings_" + setregion + " SET propid = %s, price = %s, link = %s, site = %s, timeadded = %s"
            val = (record[1], record[2], record[3], site, currenttime)
            changerecords(query, val)

            # Delete the old active one
            cursor = db.cursor()
            query = "DELETE FROM active_listings_" + setregion + " WHERE id = %s"
            val = (record[0],)
            changerecords(query,val)
    else: 
        print("No records to clean")

driver.quit()
db.close()