from fastapi import FastAPI
from fastapi.params import Body
from pydantic import BaseModel
from neo4j import GraphDatabase
import nltk
from nltk.util import ngrams
from string import Template
import time
from .database import driver
from .getlocation import get_location
#from .route import route
#from .route import route_all
#from .route import route_surface
#from .route import route_surface_bench
#from .route import route_surface_toilet
#from .route import route_surface_shelter
from . import route
from .utmTOwgs84 import converter_utm_to_wgs84



app = FastAPI()


@app.get("/")
async def root():
    return {"message": "World!!!!!!!!!!!"}

#returns one single POI
@app.get("/poi/{address}")

def location(address: str):
    loc = get_location(address)
    return {"location": loc}



#returns two POIs
@app.get("/location/{address1}/{address2}")
   
def locations(address1: str, address2: str):
    print(f"Fetching locations for {address1} and {address2}")

    loc1 = get_location (address1)
    loc2 = get_location (address2)

    type(loc1)
    type(loc2)

    print(loc1)
    print(loc2)

    return {"location1": loc1, "location2": loc2}



@app.get("/routing/{address1}/{address2}/{surface}/{bench}/{toilet}/{shelter}/{stairs}/{slope}")
def routing_new (address1: str, address2: str, surface: str, bench:str, toilet: str, shelter: str, stairs: str, slope: str):
    
    sur = int(surface)
    ben = int(bench)
    toi = int(toilet)
    she = int(shelter)
    sta = int(stairs)
    slo = int(slope)

    loc1 = get_location (address1)
    des1 = get_location (address2)

    loc_str = next(iter(loc1))
    des_str = next(iter(des1))

    print (loc_str)
    print (des_str)

    path = route.route_flexible(location=loc_str, destination=des_str, surface=sur, bench=ben, toilet=toi, shelter=she, stairs=sta, slope=slo)
    print ("path..........................")
    print ("path in main is:", path)
    path_wgs84 = converter_utm_to_wgs84(path)

    print("wgs84 path is:", path_wgs84)

    return path_wgs84


@app.get("/routenew/{address1}/{address2}/{surface}/{bench}/{toilet}/{shelter}")
def routing (address1: str, address2: str, surface: str, bench:str, toilet: str, shelter: str):
    print(f"Fetching locations for {address1} and {address2}")

    sur = int(surface)
    ben = int(bench)
    toi = int(toilet)
    she = int(shelter)

    loc1 = get_location (address1)
    des1 = get_location (address2)

    loc_str = next(iter(loc1))
    des_str = next(iter(des1))



    if sur == 1 and ben == 1 and toi == 1 and she == 1:
        path = route.route_all(location=loc_str, destination=des_str)
    elif sur == 0 and ben == 1 and toi == 1 and she == 1:
        path = route.route_surface(location=loc_str, destination=des_str)
    elif sur == 0 and ben == 0 and toi == 1 and she == 1:
        path = route.route_surface_bench(location=loc_str, destination=des_str)
    elif sur == 0 and ben == 1 and toi == 0 and she == 1:
        path = route.route_surface_toilet(location=loc_str, destination=des_str)
    elif sur == 0 and ben == 1 and toi == 1 and she == 0:
        path = route.route_surface_shelter(location=loc_str, destination=des_str)
    elif sur == 1 and ben == 0 and toi == 0 and she == 0:
        path = route.route_bench_toilet_shelter(location=loc_str, destination=des_str)
    elif sur == 1 and ben == 0 and toi == 1 and she == 1:
        path = route.route_bench(location=loc_str, destination=des_str)
    elif sur == 1 and ben == 1 and toi == 0 and she == 1:
        path = route.route_toilet(location=loc_str, destination=des_str)
    elif sur == 1 and ben == 1 and toi == 1 and she == 0:
        path = route.route_shelter(location=loc_str, destination=des_str)
    elif sur == 0 and ben == 0 and toi == 0 and she == 0:
        path = route.route_none(location=loc_str, destination=des_str)
    elif sur == 0 and ben == 0 and toi == 0 and she == 1:
        path = route.route_surface_bench_toilet(location=loc_str, destination=des_str)
    elif sur == 0 and ben == 0 and toi == 1 and she == 0:
        path = route.route_surface_bench_shelter(location=loc_str, destination=des_str)
    elif sur == 0 and ben == 1 and toi == 0 and she == 0:
        path = route.route_surface_toilet_shelter(location=loc_str, destination=des_str)
    elif sur == 1 and ben == 0 and toi == 0 and she == 1:
        path = route.route_bench_toilet(location=loc_str, destination=des_str)
    elif sur == 1 and ben == 0 and toi == 1 and she == 0:
        path = route.route_bench_shelter(location=loc_str, destination=des_str)
    elif sur == 1 and ben == 1 and toi == 0 and she == 0:
        path = route.route_toilet_shelter(location=loc_str, destination=des_str)
    
    print("here is before wgs84")
    print(path)




    path_wgs84 = converter_utm_to_wgs84(path)

    print("wgs84 path is:", path_wgs84)

    return path_wgs84





@app.get("/all")
def get_locations():
    try:
        with driver.session(database="kiss-new2") as session:
            query = "MATCH (n:Address) RETURN n.full_address AS node_address LIMIT 10"
            result = session.run(query)
            
            node_addresses = []  # Initialize outside the loop

            for record in result:
                if record["node_address"] is not None:
                    node_addresses.append(record["node_address"])

            return {"node_address": node_addresses}

    except Exception as e:
        return {"error": str(e)}

    finally:
        driver.close()


