import mysql.connector
import time
import os

# DB
sqluser = os.environ["MYSQL_USER"]
sqlpass = os.environ["MYSQL_PASS"]

db = mysql.connector.connect(
    host = "localhost",
    user = sqluser,
    password = sqlpass,
    database = "prod_proplist"
)

# Get existing listings older than 24 hours
currenttime = time.time()
cursor = db.cursor()
query = "SELECT * FROM active_listings_johnsonville WHERE lastscan < %s"
val = ((currenttime - 86400),)
cursor.execute(query, val)
oldrecord = cursor.fetchall()
cursor.close()

if len(oldrecord) != 0:
    for record in oldrecord:

        # Move the current active into the prior record table
        cursor = db.cursor()
        query = "INSERT INTO prior_listings_johnsonville SET propid = %s, price = %s, link = %s, timeadded = %s"
        val = (record[1], record[2], record[3], currenttime)
        cursor.execute(query, val)
        db.commit()
        cursor.close()

        # Delete the old active one
        cursor = db.cursor()
        query = "DELETE FROM active_listings_johnsonville WHERE id = %s"
        val = (record[0],)
        cursor.execute(query, val)
        db.commit()
        cursor.close()

        # Update the property record
        cursor = db.cursor()
        query = "UPDATE propertylist_johnsonville SET active = 0 WHERE id = %s"
        val = (record[1],)
        cursor.execute(query, val)
        db.commit()
        cursor.close()
else: 
    print("No records to clean")

db.close()