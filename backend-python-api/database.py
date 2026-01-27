from neo4j import GraphDatabase
import time

#Database connection

while True:
    try:
        uri = "bolt://localhost:***"  # Update if using a different port
        username = "***"
        password = "***"
        # Initialize Neo4j driver once and reuse it
        driver = GraphDatabase.driver(uri, auth=(***, ***))
        print("Database connection was succesful!")
        break

    except Exception as error:
        print("connection to database failed")
        print("Error: ", error)
        time.sleep(2)