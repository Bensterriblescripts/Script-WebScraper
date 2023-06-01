import mysql.connector
import os
import time

sqluser = os.environ["MYSQL_USER"]
sqlpass = os.environ["MYSQL_PASS"]
db = mysql.connector.connect(
    host = "localhost",
    user = sqluser,
    password = sqlpass,
    database = "prod_proplistings"
)
currenttime = time.time()

# Get the scan records
cursor = db.cursor()
query = "SELECT * FROM scan_trademe_johnsonville"
cursor.execute(query)
scans = cursor.fetchall()
cursor.close()

for record in scans:
    cursor = db.cursor()
    query = "SELECT * FROM proplist_johnsonville WHERE addr = %s AND suburb = %s AND region = %s AND city = %s"
    val = (record[1], record[2], record[3], record[4])
    cursor.execute(query, val)
    proprecord = cursor.fetchall()
    cursor.close()

    # Insert a new record
    if len(proprecord) == 0:
        cursor = db.cursor()
        query = "INSERT INTO proplist_johnsonville SET addr = %s, suburb = %s, region = %s, city = %s, activelisting = %s, price = %s, count = 1"
        val = (record[1], record[2], record[3], record[4], record[6], record[5])
        cursor.execute(query, val)
        db.commit()
        cursor.close()
        # Delete the scan record
        cursor = db.cursor()
        query = "DELETE FROM scan_trademe_johnsonville WHERE id = %s"
        val = (record[0],)
        cursor.execute(query, val)
        db.commit()
        cursor.close()

    # Update the existing record
    else: 
        # If the price is the same and the scan is less than 24 hours old, do nothing.
        if proprecord[6] == record[5] and (currenttime - 86400) < record[7]:
            continue
        # Price change
        elif proprecord[6] != record[5]


    



db.close()