import mysql.connector
import os
import statistics

# DB
sqluser = os.environ["MYSQL_USER"]
sqlpass = os.environ["MYSQL_PASS"]

db = mysql.connector.connect(
    host = "localhost",
    user = sqluser,
    password = sqlpass,
    database = "prod_proplist"
)

def getAverages(table):
    # Import a suburb list later to streamline this
    cursor = db.cursor()
    query = f"SELECT price FROM propertylist_{table}"
    cursor.execute(query)
    propertyrecord = cursor.fetchall()
    cursor.close()

    # Remove the stupidly designed $ to create an int
    johnsonville = []
    for record in propertyrecord:
        if record[0] == "Not Listed":
            continue
        else: 
            basestr = record[0].replace("$", "").replace(",", "")
            baseint = int(basestr)
            johnsonville.append(baseint)

    medianrawjohnsonville = statistics.median(johnsonville)
    medianjohnsonville = round(medianrawjohnsonville)

    averagerawjohnsonville = statistics.mean(johnsonville)
    averagejohnsonville = round(averagerawjohnsonville)

    print("Median: ", medianjohnsonville)
    print("Average: ", averagejohnsonville, "\n")

tables = ['johnsonville', 'khandallah']
for table in tables:
    tablename = table.capitalize()
    print(tablename)
    getAverages(table)

db.close()