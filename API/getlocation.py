from neo4j import GraphDatabase
import nltk
from nltk.util import ngrams
from string import Template
import time
from .database import driver

#for finding one node
def get_location (address: str):
    print("done")
    try:
        with driver.session(database="kiss-new2") as session:
            query =  """
                MATCH (n)
                WITH n, 
                    apoc.text.clean(n.full_address) AS db_address, 
                    apoc.text.clean($address) AS input_address
                WITH n.full_address AS poi_address, elementId(n) AS node_id,
                    apoc.text.levenshteinDistance(db_address, input_address) AS distance,
                    size(db_address) AS len_db, 
                    size(input_address) AS len_input
                WITH poi_address, node_id, distance, 
                    (1.0 - toFloat(distance) / toFloat(apoc.coll.max([len_db, len_input]))) AS similarity
                WHERE similarity >= 0.8
                ORDER BY similarity DESC
                LIMIT 1
                RETURN poi_address;
                """
            result = session.run(query, address=address)
            record = result.single()
            print(record["poi_address"])            

            return {record["poi_address"]}

    except Exception as e:
        print("error2")
        return {"error": "Ort nicht gefunden!!!"}

    finally:
        driver.close()