from neo4j import GraphDatabase
import nltk
from nltk.util import ngrams
from string import Template
import time
from .database import driver

#route new Method
def route_flexible(location: str, destination: str, surface: int, bench: int, toilet: int, shelter: int, stairs: int, slope: int):

    print("route flex is called")

    print ("location is:", location)
    print ("destination is:", destination)

    if surface == 1:
        surface_entry = {"surface": { "asphalt": 1.0, "gravel": 2.0, "grass": 2.5}}
    else: surface_entry = {}
    print ("surface_entry is:", surface_entry)

    if slope == 1:
        slope_entry =  [{ "name": "flach", "maxSlope": 3.0, "upWeight": 1.0, "downWeight": 1.0 }, { "name": "mittel", "maxSlope": 7.0, "upWeight": 1.5, "downWeight": 1.2 }, { "name": "steil", "maxSlope": 12.0, "upWeight": 2.0, "downWeight": 1.4 }]
    else: slope_entry = []

    print ("slope_entry is:", slope_entry)

    if stairs == 1:
        stairs_entry = { "highway": ["steps"] }
    else: stairs_entry = {}
    print ("stairs_entry is:", stairs_entry)

    betosh_entry = {}
    if bench == 1:
        betosh_entry["bench"] = { "maxDistance": 100.0, "maxInterval": 500.0, "importance": 1.5 }
    if toilet == 1:
        betosh_entry["toilet"] = { "maxDistance": 80.0, "maxInterval": 1000.0, "importance": 3.0 }
    if shelter == 1:
        betosh_entry["shelter"] = { "maxDistance": 150.0, "maxInterval": 1000.0, "importance": 1.1 }

    print ("betosh_entry is:", betosh_entry)

    try:
        with driver.session(database="kiss-new2") as session:
            query =  """
            MATCH (a:Address)-[:NEAREST_INTERSECTION]->(start:Point)
            WHERE a.full_address CONTAINS $loc
            MATCH (b:Address)-[:NEAREST_INTERSECTION]->(end:Point)
            WHERE b.full_address CONTAINS $des
            
            CALL org.kiss.flexibleWeightedShortestPath(
            elementId(start),
            elementId(end),
            "x", "y",
            $slopes ,
            $surfaces ,
            $steps ,
            $betosh
            )
            YIELD path, totalDistance, weightedDistance, poiCount, poiDetails, warnings, routeQuality
            RETURN
            path,
            routeQuality,
            totalDistance,
            warnings,
            poiCount,
            [poi in poiDetails | {
            poi_type: poi.type,
            x: poi.location.x,
            y: poi.location.y 
            }] as poiDetail;
                """
            result = session.run(query, loc = location, des = destination, slopes = slope_entry, surfaces = surface_entry, steps = stairs_entry, betosh = betosh_entry)
            print ("result is:", result)
            record = result.single()
            

            return {"path":record["path"],
                    "routeQuality": record["routeQuality"],
                    "totalDistance": record["totalDistance"],
                    "warnings": record["warnings"],
                    "poiCount":record["poiCount"],
                    "poiDetail":record["poiDetail"]}

    except Exception as e:
        print("error3")
        return {"error": "Route nicht gefunden!!!"}

    finally:
        driver.close()



#for finding route
def route (location: str, destination: str):
    print("done")
    try:
        with driver.session(database="kiss-new2") as session:
            query =  """
            MATCH (a:Address)-[:NEAREST_INTERSECTION]->(source:Point) 
            WHERE a.full_address CONTAINS $loc
            MATCH (poi:Address)-[:NEAREST_INTERSECTION]->(dest:Point) 
            WHERE poi.full_address CONTAINS $des 
            CALL org.kiss.shortestPathAStarWithPOI(
            elementId(source), 
            elementId(dest), 
            "latitude", 
            "longitude", 
            {length: 1.0, slope: 2.5},
            {highway: ["steps"]},
            [],
            0.0,
            false,
            false
            ) YIELD path, totalDistance, weightedDistance, metrics
            RETURN
            path,
            totalDistance,
            weightedDistance;
                """
            result = session.run(query, loc = location, des = destination)
            record = result.single()
            print("It is here")
            print("result:", result)
            print("Record:", record)         
            print("It is here 2")

            return {"path": record["path"],
                    "totalDistance": record["totalDistance"],
                    "weightedDistance": record["weightedDistance"]}

    except Exception as e:
        print("error3")
        return {"error": "Route nicht gefunden!!!"}

    finally:
        driver.close()


#for finding route with surface, bench, toilet and shelter
def route_all (location: str, destination: str):
    
    try:
        with driver.session(database="kiss-new2") as session:
            query =  """
            MATCH (a:Address)-[:NEAREST_INTERSECTION]->(start:Point)
            WHERE a.full_address CONTAINS $loc
            MATCH (b:Address)-[:NEAREST_INTERSECTION]->(end:Point)
            WHERE b.full_address CONTAINS $des
            
            CALL org.kiss.flexibleWeightedShortestPath(
            elementId(start),
            elementId(end),
            "x", "y",
            [
            { name: "flach", maxSlope: 3.0, upWeight: 1.0, downWeight: 1.0 },
            { name: "mittel", maxSlope: 7.0, upWeight: 1.5, downWeight: 1.2 },
            { name: "steil", maxSlope: 12.0, upWeight: 2.0, downWeight: 1.4 }
            ],
            {surface: { asphalt: 1.0, gravel: 2.0, grass: 2.5}},
            { highway: ["steps"] },
            {
            bench: { maxDistance: 100.0, maxInterval: 500.0, importance: 1.5 },
            toilet: { maxDistance: 80.0, maxInterval: 1000.0, importance: 3.0 },
            shelter:{ maxDistance: 150.0, maxInterval: 1000.0, importance: 1.1 }
            }
            )
            YIELD path, totalDistance, weightedDistance, poiCount, poiDetails, warnings, routeQuality
            RETURN
            path,
            routeQuality,
            totalDistance,
            warnings,
            poiCount,
            [poi in poiDetails | {
            poi_type: poi.type,
            x: poi.location.x,
            y: poi.location.y 
            }] as poiDetail;
                """
            result = session.run(query, loc = location, des = destination)
            record = result.single()
            

            return {"path":record["path"],
                    "routeQuality": record["routeQuality"],
                    "totalDistance": record["totalDistance"],
                    "warnings": record["warnings"],
                    "poiCount":record["poiCount"],
                    "poiDetail":record["poiDetail"]}

    except Exception as e:
        print("error3")
        return {"error": "Route nicht gefunden!!!"}

    finally:
        driver.close()


#for finding route with without surface, bench, toilet and shelter
def route_surface (location: str, destination: str):
    
    try:
        with driver.session(database="kiss-new2") as session:
            query =  """
            MATCH (a:Address)-[:NEAREST_INTERSECTION]->(start:Point)
            WHERE a.full_address CONTAINS $loc
            MATCH (b:Address)-[:NEAREST_INTERSECTION]->(end:Point)
            WHERE b.full_address CONTAINS $des
            
            CALL org.kiss.flexibleWeightedShortestPath(
            elementId(start),
            elementId(end),
            "x", "y",
            [
            { name: "flach", maxSlope: 3.0, upWeight: 1.0, downWeight: 1.0 },
            { name: "mittel", maxSlope: 7.0, upWeight: 1.5, downWeight: 1.2 },
            { name: "steil", maxSlope: 12.0, upWeight: 2.0, downWeight: 1.4 }
            ],
            {},
            { highway: ["steps"] },
            {
            bench: { maxDistance: 100.0, maxInterval: 500.0, importance: 1.5 },
            toilet: { maxDistance: 80.0, maxInterval: 1000.0, importance: 3.0 },
            shelter:{ maxDistance: 150.0, maxInterval: 1000.0, importance: 1.1 }
            }
            )
            YIELD path, totalDistance, weightedDistance, poiCount, poiDetails, warnings, routeQuality
            RETURN
            path,
            routeQuality,
            totalDistance,
            warnings,
            poiCount,
            [poi in poiDetails | {
            poi_type: poi.type,
            x: poi.location.x,
            y: poi.location.y 
            }] as poiDetail;
                """
            result = session.run(query, loc = location, des = destination)
            record = result.single()
            

            return {"path":record["path"],
                    "routeQuality": record["routeQuality"],
                    "totalDistance": record["totalDistance"],
                    "warnings": record["warnings"],
                    "poiCount":record["poiCount"],
                    "poiDetail":record["poiDetail"]}

    except Exception as e:
        print("error3")
        return {"error": "Route nicht gefunden!!!"}

    finally:
        driver.close()

#for finding route with without surface and bench, with toilet and shelter
def route_surface_bench (location: str, destination: str):
    
    try:
        with driver.session(database="kiss-new2") as session:
            query =  """
            MATCH (a:Address)-[:NEAREST_INTERSECTION]->(start:Point)
            WHERE a.full_address CONTAINS $loc
            MATCH (b:Address)-[:NEAREST_INTERSECTION]->(end:Point)
            WHERE b.full_address CONTAINS $des
            
            CALL org.kiss.flexibleWeightedShortestPath(
            elementId(start),
            elementId(end),
            "x", "y",
            [
            { name: "flach", maxSlope: 3.0, upWeight: 1.0, downWeight: 1.0 },
            { name: "mittel", maxSlope: 7.0, upWeight: 1.5, downWeight: 1.2 },
            { name: "steil", maxSlope: 12.0, upWeight: 2.0, downWeight: 1.4 }
            ],
            {},
            { highway: ["steps"] },
            {
            toilet: { maxDistance: 80.0, maxInterval: 1000.0, importance: 3.0 },
            shelter:{ maxDistance: 150.0, maxInterval: 1000.0, importance: 1.1 }
            }
            )
            YIELD path, totalDistance, weightedDistance, poiCount, poiDetails, warnings, routeQuality
            RETURN
            path,
            routeQuality,
            totalDistance,
            warnings,
            poiCount,
            [poi in poiDetails | {
            poi_type: poi.type,
            x: poi.location.x,
            y: poi.location.y 
            }] as poiDetail;
                """
            result = session.run(query, loc = location, des = destination)
            record = result.single()
            

            return {"path":record["path"],
                    "routeQuality": record["routeQuality"],
                    "totalDistance": record["totalDistance"],
                    "warnings": record["warnings"],
                    "poiCount":record["poiCount"],
                    "poiDetail":record["poiDetail"]}

    except Exception as e:
        print("error3")
        return {"error": "Route nicht gefunden!!!"}

    finally:
        driver.close()


#for finding route with without surface and toilet, with bench and shelter
def route_surface_toilet (location: str, destination: str):
    
    try:
        with driver.session(database="kiss-new2") as session:
            query =  """
            MATCH (a:Address)-[:NEAREST_INTERSECTION]->(start:Point)
            WHERE a.full_address CONTAINS $loc
            MATCH (b:Address)-[:NEAREST_INTERSECTION]->(end:Point)
            WHERE b.full_address CONTAINS $des
            
            CALL org.kiss.flexibleWeightedShortestPath(
            elementId(start),
            elementId(end),
            "x", "y",
            [
            { name: "flach", maxSlope: 3.0, upWeight: 1.0, downWeight: 1.0 },
            { name: "mittel", maxSlope: 7.0, upWeight: 1.5, downWeight: 1.2 },
            { name: "steil", maxSlope: 12.0, upWeight: 2.0, downWeight: 1.4 }
            ],
            {},
            { highway: ["steps"] },
            {
            bench: { maxDistance: 100.0, maxInterval: 500.0, importance: 1.5 },
            shelter:{ maxDistance: 150.0, maxInterval: 1000.0, importance: 1.1 }
            }
            )
            YIELD path, totalDistance, weightedDistance, poiCount, poiDetails, warnings, routeQuality
            RETURN
            path,
            routeQuality,
            totalDistance,
            warnings,
            poiCount,
            [poi in poiDetails | {
            poi_type: poi.type,
            x: poi.location.x,
            y: poi.location.y 
            }] as poiDetail;
                """
            result = session.run(query, loc = location, des = destination)
            record = result.single()
            

            return {"path":record["path"],
                    "routeQuality": record["routeQuality"],
                    "totalDistance": record["totalDistance"],
                    "warnings": record["warnings"],
                    "poiCount":record["poiCount"],
                    "poiDetail":record["poiDetail"]}

    except Exception as e:
        print("error3")
        return {"error": "Route nicht gefunden!!!"}

    finally:
        driver.close()

#for finding route with without surface and shelter, with bench and toilet
def route_surface_shelter (location: str, destination: str):
    
    try:
        with driver.session(database="kiss-new2") as session:
            query =  """
            MATCH (a:Address)-[:NEAREST_INTERSECTION]->(start:Point)
            WHERE a.full_address CONTAINS $loc
            MATCH (b:Address)-[:NEAREST_INTERSECTION]->(end:Point)
            WHERE b.full_address CONTAINS $des
            
            CALL org.kiss.flexibleWeightedShortestPath(
            elementId(start),
            elementId(end),
            "x", "y",
            [
            { name: "flach", maxSlope: 3.0, upWeight: 1.0, downWeight: 1.0 },
            { name: "mittel", maxSlope: 7.0, upWeight: 1.5, downWeight: 1.2 },
            { name: "steil", maxSlope: 12.0, upWeight: 2.0, downWeight: 1.4 }
            ],
            {},
            { highway: ["steps"] },
            {
            bench: { maxDistance: 100.0, maxInterval: 500.0, importance: 1.5 },
            toilet: { maxDistance: 80.0, maxInterval: 1000.0, importance: 3.0 }
            }
            )
            YIELD path, totalDistance, weightedDistance, poiCount, poiDetails, warnings, routeQuality
            RETURN
            path,
            routeQuality,
            totalDistance,
            warnings,
            poiCount,
            [poi in poiDetails | {
            poi_type: poi.type,
            x: poi.location.x,
            y: poi.location.y 
            }] as poiDetail;
                """
            result = session.run(query, loc = location, des = destination)
            record = result.single()
            

            return {"path":record["path"],
                    "routeQuality": record["routeQuality"],
                    "totalDistance": record["totalDistance"],
                    "warnings": record["warnings"],
                    "poiCount":record["poiCount"],
                    "poiDetail":record["poiDetail"]}

    except Exception as e:
        print("error3")
        return {"error": "Route nicht gefunden!!!"}

    finally:
        driver.close()

#for finding route with surface and without toilet, bench and shelter
def route_bench_toilet_shelter (location: str, destination: str):
    
    try:
        with driver.session(database="kiss-new2") as session:
            query =  """
            MATCH (a:Address)-[:NEAREST_INTERSECTION]->(start:Point)
            WHERE a.full_address CONTAINS $loc
            MATCH (b:Address)-[:NEAREST_INTERSECTION]->(end:Point)
            WHERE b.full_address CONTAINS $des
            
            CALL org.kiss.flexibleWeightedShortestPath(
            elementId(start),
            elementId(end),
            "x", "y",
            [
            { name: "flach", maxSlope: 3.0, upWeight: 1.0, downWeight: 1.0 },
            { name: "mittel", maxSlope: 7.0, upWeight: 1.5, downWeight: 1.2 },
            { name: "steil", maxSlope: 12.0, upWeight: 2.0, downWeight: 1.4 }
            ],
            {surface: { asphalt: 1.0, gravel: 2.0, grass: 2.5}},
            { highway: ["steps"] },
            {
            }
            )
            YIELD path, totalDistance, weightedDistance, poiCount, poiDetails, warnings, routeQuality
            RETURN
            path,
            routeQuality,
            totalDistance,
            warnings,
            poiCount,
            [poi in poiDetails | {
            poi_type: poi.type,
            x: poi.location.x,
            y: poi.location.y 
            }] as poiDetail;
                """
            result = session.run(query, loc = location, des = destination)
            record = result.single()
            

            return {"path":record["path"],
                    "routeQuality": record["routeQuality"],
                    "totalDistance": record["totalDistance"],
                    "warnings": record["warnings"],
                    "poiCount":record["poiCount"],
                    "poiDetail":record["poiDetail"]}

    except Exception as e:
        print("error3")
        return {"error": "Route nicht gefunden!!!"}

    finally:
        driver.close()

#for finding route with surface, toilet and shelter without bench
def route_bench (location: str, destination: str):
    
    try:
        with driver.session(database="kiss-new2") as session:
            query =  """
            MATCH (a:Address)-[:NEAREST_INTERSECTION]->(start:Point)
            WHERE a.full_address CONTAINS $loc
            MATCH (b:Address)-[:NEAREST_INTERSECTION]->(end:Point)
            WHERE b.full_address CONTAINS $des
            
            CALL org.kiss.flexibleWeightedShortestPath(
            elementId(start),
            elementId(end),
            "x", "y",
            [
            { name: "flach", maxSlope: 3.0, upWeight: 1.0, downWeight: 1.0 },
            { name: "mittel", maxSlope: 7.0, upWeight: 1.5, downWeight: 1.2 },
            { name: "steil", maxSlope: 12.0, upWeight: 2.0, downWeight: 1.4 }
            ],
            {surface: { asphalt: 1.0, gravel: 2.0, grass: 2.5}},
            { highway: ["steps"] },
            {
            toilet: { maxDistance: 80.0, maxInterval: 1000.0, importance: 3.0 },
            shelter:{ maxDistance: 150.0, maxInterval: 1000.0, importance: 1.1 }
            }
            )
            YIELD path, totalDistance, weightedDistance, poiCount, poiDetails, warnings, routeQuality
            RETURN
            path,
            routeQuality,
            totalDistance,
            warnings,
            poiCount,
            [poi in poiDetails | {
            poi_type: poi.type,
            x: poi.location.x,
            y: poi.location.y 
            }] as poiDetail;
                """
            result = session.run(query, loc = location, des = destination)
            record = result.single()
            

            return {"path":record["path"],
                    "routeQuality": record["routeQuality"],
                    "totalDistance": record["totalDistance"],
                    "warnings": record["warnings"],
                    "poiCount":record["poiCount"],
                    "poiDetail":record["poiDetail"]}

    except Exception as e:
        print("error3")
        return {"error": "Route nicht gefunden!!!"}

    finally:
        driver.close()

#for finding route with surface, bench and shelter, without toilet
def route_toilet (location: str, destination: str):
    
    try:
        with driver.session(database="kiss-new2") as session:
            query =  """
            MATCH (a:Address)-[:NEAREST_INTERSECTION]->(start:Point)
            WHERE a.full_address CONTAINS $loc
            MATCH (b:Address)-[:NEAREST_INTERSECTION]->(end:Point)
            WHERE b.full_address CONTAINS $des
            
            CALL org.kiss.flexibleWeightedShortestPath(
            elementId(start),
            elementId(end),
            "x", "y",
            [
            { name: "flach", maxSlope: 3.0, upWeight: 1.0, downWeight: 1.0 },
            { name: "mittel", maxSlope: 7.0, upWeight: 1.5, downWeight: 1.2 },
            { name: "steil", maxSlope: 12.0, upWeight: 2.0, downWeight: 1.4 }
            ],
            {surface: { asphalt: 1.0, gravel: 2.0, grass: 2.5}},
            { highway: ["steps"] },
            {
            bench: { maxDistance: 100.0, maxInterval: 500.0, importance: 1.5 },
            shelter:{ maxDistance: 150.0, maxInterval: 1000.0, importance: 1.1 }
            }
            )
            YIELD path, totalDistance, weightedDistance, poiCount, poiDetails, warnings, routeQuality
            RETURN
            path,
            routeQuality,
            totalDistance,
            warnings,
            poiCount,
            [poi in poiDetails | {
            poi_type: poi.type,
            x: poi.location.x,
            y: poi.location.y 
            }] as poiDetail;
                """
            result = session.run(query, loc = location, des = destination)
            record = result.single()
            

            return {"path":record["path"],
                    "routeQuality": record["routeQuality"],
                    "totalDistance": record["totalDistance"],
                    "warnings": record["warnings"],
                    "poiCount":record["poiCount"],
                    "poiDetail":record["poiDetail"]}

    except Exception as e:
        print("error3")
        return {"error": "Route nicht gefunden!!!"}

    finally:
        driver.close()

#for finding route with surface, bench and toilet, without shelter
def route_shelter (location: str, destination: str):
    
    try:
        with driver.session(database="kiss-new2") as session:
            query =  """
            MATCH (a:Address)-[:NEAREST_INTERSECTION]->(start:Point)
            WHERE a.full_address CONTAINS $loc
            MATCH (b:Address)-[:NEAREST_INTERSECTION]->(end:Point)
            WHERE b.full_address CONTAINS $des
            
            CALL org.kiss.flexibleWeightedShortestPath(
            elementId(start),
            elementId(end),
            "x", "y",
            [
            { name: "flach", maxSlope: 3.0, upWeight: 1.0, downWeight: 1.0 },
            { name: "mittel", maxSlope: 7.0, upWeight: 1.5, downWeight: 1.2 },
            { name: "steil", maxSlope: 12.0, upWeight: 2.0, downWeight: 1.4 }
            ],
            {surface: { asphalt: 1.0, gravel: 2.0, grass: 2.5}},
            { highway: ["steps"] },
            {
            bench: { maxDistance: 100.0, maxInterval: 500.0, importance: 1.5 },
            toilet: { maxDistance: 80.0, maxInterval: 1000.0, importance: 3.0 }
            }
            )
            YIELD path, totalDistance, weightedDistance, poiCount, poiDetails, warnings, routeQuality
            RETURN
            path,
            routeQuality,
            totalDistance,
            warnings,
            poiCount,
            [poi in poiDetails | {
            poi_type: poi.type,
            x: poi.location.x,
            y: poi.location.y 
            }] as poiDetail;
                """
            result = session.run(query, loc = location, des = destination)
            record = result.single()
            

            return {"path":record["path"],
                    "routeQuality": record["routeQuality"],
                    "totalDistance": record["totalDistance"],
                    "warnings": record["warnings"],
                    "poiCount":record["poiCount"],
                    "poiDetail":record["poiDetail"]}

    except Exception as e:
        print("error3")
        return {"error": "Route nicht gefunden!!!"}

    finally:
        driver.close()


#for finding route without surface, bench, toilet and shelter
def route_none (location: str, destination: str):
    
    try:
        with driver.session(database="kiss-new2") as session:
            query =  """
            MATCH (a:Address)-[:NEAREST_INTERSECTION]->(start:Point)
            WHERE a.full_address CONTAINS $loc
            MATCH (b:Address)-[:NEAREST_INTERSECTION]->(end:Point)
            WHERE b.full_address CONTAINS $des
            
            CALL org.kiss.flexibleWeightedShortestPath(
            elementId(start),
            elementId(end),
            "x", "y",
            [
            { name: "flach", maxSlope: 3.0, upWeight: 1.0, downWeight: 1.0 },
            { name: "mittel", maxSlope: 7.0, upWeight: 1.5, downWeight: 1.2 },
            { name: "steil", maxSlope: 12.0, upWeight: 2.0, downWeight: 1.4 }
            ],
            {},
            { highway: ["steps"] },
            {
            }
            )
            YIELD path, totalDistance, weightedDistance, poiCount, poiDetails, warnings, routeQuality
            RETURN
            path,
            routeQuality,
            totalDistance,
            warnings,
            poiCount,
            [poi in poiDetails | {
            poi_type: poi.type,
            x: poi.location.x,
            y: poi.location.y 
            }] as poiDetail;
                """
            result = session.run(query, loc = location, des = destination)
            record = result.single()
            

            return {"path":record["path"],
                    "routeQuality": record["routeQuality"],
                    "totalDistance": record["totalDistance"],
                    "warnings": record["warnings"],
                    "poiCount":record["poiCount"],
                    "poiDetail":record["poiDetail"]}

    except Exception as e:
        print("error3")
        return {"error": "Route nicht gefunden!!!"}

    finally:
        driver.close()

#for finding route without surface, bench and toilet and with shelter
def route_surface_bench_toilet (location: str, destination: str):
    
    try:
        with driver.session(database="kiss-new2") as session:
            query =  """
            MATCH (a:Address)-[:NEAREST_INTERSECTION]->(start:Point)
            WHERE a.full_address CONTAINS $loc
            MATCH (b:Address)-[:NEAREST_INTERSECTION]->(end:Point)
            WHERE b.full_address CONTAINS $des
            
            CALL org.kiss.flexibleWeightedShortestPath(
            elementId(start),
            elementId(end),
            "x", "y",
            [
            { name: "flach", maxSlope: 3.0, upWeight: 1.0, downWeight: 1.0 },
            { name: "mittel", maxSlope: 7.0, upWeight: 1.5, downWeight: 1.2 },
            { name: "steil", maxSlope: 12.0, upWeight: 2.0, downWeight: 1.4 }
            ],
            {},
            { highway: ["steps"] },
            {
            shelter:{ maxDistance: 150.0, maxInterval: 1000.0, importance: 1.1 }
            }
            )
            YIELD path, totalDistance, weightedDistance, poiCount, poiDetails, warnings, routeQuality
            RETURN
            path,
            routeQuality,
            totalDistance,
            warnings,
            poiCount,
            [poi in poiDetails | {
            poi_type: poi.type,
            x: poi.location.x,
            y: poi.location.y 
            }] as poiDetail;
                """
            result = session.run(query, loc = location, des = destination)
            record = result.single()
            

            return {"path":record["path"],
                    "routeQuality": record["routeQuality"],
                    "totalDistance": record["totalDistance"],
                    "warnings": record["warnings"],
                    "poiCount":record["poiCount"],
                    "poiDetail":record["poiDetail"]}

    except Exception as e:
        print("error3")
        return {"error": "Route nicht gefunden!!!"}

    finally:
        driver.close()

#for finding route without surface, bench, and shelter and with toilet
def route_surface_bench_shelter (location: str, destination: str):
    
    try:
        with driver.session(database="kiss-new2") as session:
            query =  """
            MATCH (a:Address)-[:NEAREST_INTERSECTION]->(start:Point)
            WHERE a.full_address CONTAINS $loc
            MATCH (b:Address)-[:NEAREST_INTERSECTION]->(end:Point)
            WHERE b.full_address CONTAINS $des
            
            CALL org.kiss.flexibleWeightedShortestPath(
            elementId(start),
            elementId(end),
            "x", "y",
            [
            { name: "flach", maxSlope: 3.0, upWeight: 1.0, downWeight: 1.0 },
            { name: "mittel", maxSlope: 7.0, upWeight: 1.5, downWeight: 1.2 },
            { name: "steil", maxSlope: 12.0, upWeight: 2.0, downWeight: 1.4 }
            ],
            {},
            { highway: ["steps"] },
            {
            toilet: { maxDistance: 80.0, maxInterval: 1000.0, importance: 3.0 }
            }
            )
            YIELD path, totalDistance, weightedDistance, poiCount, poiDetails, warnings, routeQuality
            RETURN
            path,
            routeQuality,
            totalDistance,
            warnings,
            poiCount,
            [poi in poiDetails | {
            poi_type: poi.type,
            x: poi.location.x,
            y: poi.location.y 
            }] as poiDetail;
                """
            result = session.run(query, loc = location, des = destination)
            record = result.single()
            

            return {"path":record["path"],
                    "routeQuality": record["routeQuality"],
                    "totalDistance": record["totalDistance"],
                    "warnings": record["warnings"],
                    "poiCount":record["poiCount"],
                    "poiDetail":record["poiDetail"]}

    except Exception as e:
        print("error3")
        return {"error": "Route nicht gefunden!!!"}

    finally:
        driver.close()

#for finding route without surface, toilet and shelter and with bench
def route_surface_toilet_shelter (location: str, destination: str):
    
    try:
        with driver.session(database="kiss-new2") as session:
            query =  """
            MATCH (a:Address)-[:NEAREST_INTERSECTION]->(start:Point)
            WHERE a.full_address CONTAINS $loc
            MATCH (b:Address)-[:NEAREST_INTERSECTION]->(end:Point)
            WHERE b.full_address CONTAINS $des
            
            CALL org.kiss.flexibleWeightedShortestPath(
            elementId(start),
            elementId(end),
            "x", "y",
            [
            { name: "flach", maxSlope: 3.0, upWeight: 1.0, downWeight: 1.0 },
            { name: "mittel", maxSlope: 7.0, upWeight: 1.5, downWeight: 1.2 },
            { name: "steil", maxSlope: 12.0, upWeight: 2.0, downWeight: 1.4 }
            ],
            {},
            { highway: ["steps"] },
            {
            bench: { maxDistance: 100.0, maxInterval: 500.0, importance: 1.5 }
            }
            )
            YIELD path, totalDistance, weightedDistance, poiCount, poiDetails, warnings, routeQuality
            RETURN
            path,
            routeQuality,
            totalDistance,
            warnings,
            poiCount,
            [poi in poiDetails | {
            poi_type: poi.type,
            x: poi.location.x,
            y: poi.location.y 
            }] as poiDetail;
                """
            result = session.run(query, loc = location, des = destination)
            record = result.single()
            

            return {"path":record["path"],
                    "routeQuality": record["routeQuality"],
                    "totalDistance": record["totalDistance"],
                    "warnings": record["warnings"],
                    "poiCount":record["poiCount"],
                    "poiDetail":record["poiDetail"]}

    except Exception as e:
        print("error3")
        return {"error": "Route nicht gefunden!!!"}

    finally:
        driver.close()

#for finding route with surface and shelter without bench and toilet
def route_bench_toilet (location: str, destination: str):
    
    try:
        with driver.session(database="kiss-new2") as session:
            query =  """
            MATCH (a:Address)-[:NEAREST_INTERSECTION]->(start:Point)
            WHERE a.full_address CONTAINS $loc
            MATCH (b:Address)-[:NEAREST_INTERSECTION]->(end:Point)
            WHERE b.full_address CONTAINS $des
            
            CALL org.kiss.flexibleWeightedShortestPath(
            elementId(start),
            elementId(end),
            "x", "y",
            [
            { name: "flach", maxSlope: 3.0, upWeight: 1.0, downWeight: 1.0 },
            { name: "mittel", maxSlope: 7.0, upWeight: 1.5, downWeight: 1.2 },
            { name: "steil", maxSlope: 12.0, upWeight: 2.0, downWeight: 1.4 }
            ],
            {surface: { asphalt: 1.0, gravel: 2.0, grass: 2.5}},
            { highway: ["steps"] },
            {
            shelter:{ maxDistance: 150.0, maxInterval: 1000.0, importance: 1.1 }
            }
            )
            YIELD path, totalDistance, weightedDistance, poiCount, poiDetails, warnings, routeQuality
            RETURN
            path,
            routeQuality,
            totalDistance,
            warnings,
            poiCount,
            [poi in poiDetails | {
            poi_type: poi.type,
            x: poi.location.x,
            y: poi.location.y 
            }] as poiDetail;
                """
            result = session.run(query, loc = location, des = destination)
            record = result.single()
            

            return {"path":record["path"],
                    "routeQuality": record["routeQuality"],
                    "totalDistance": record["totalDistance"],
                    "warnings": record["warnings"],
                    "poiCount":record["poiCount"],
                    "poiDetail":record["poiDetail"]}

    except Exception as e:
        print("error3")
        return {"error": "Route nicht gefunden!!!"}

    finally:
        driver.close()

#for finding route with surface and toilet, without bench and shelter
def route_bench_shelter (location: str, destination: str):
    
    try:
        with driver.session(database="kiss-new2") as session:
            query =  """
            MATCH (a:Address)-[:NEAREST_INTERSECTION]->(start:Point)
            WHERE a.full_address CONTAINS $loc
            MATCH (b:Address)-[:NEAREST_INTERSECTION]->(end:Point)
            WHERE b.full_address CONTAINS $des
            
            CALL org.kiss.flexibleWeightedShortestPath(
            elementId(start),
            elementId(end),
            "x", "y",
            [
            { name: "flach", maxSlope: 3.0, upWeight: 1.0, downWeight: 1.0 },
            { name: "mittel", maxSlope: 7.0, upWeight: 1.5, downWeight: 1.2 },
            { name: "steil", maxSlope: 12.0, upWeight: 2.0, downWeight: 1.4 }
            ],
            {surface: { asphalt: 1.0, gravel: 2.0, grass: 2.5}},
            { highway: ["steps"] },
            {
            toilet: { maxDistance: 80.0, maxInterval: 1000.0, importance: 3.0 }
            }
            )
            YIELD path, totalDistance, weightedDistance, poiCount, poiDetails, warnings, routeQuality
            RETURN
            path,
            routeQuality,
            totalDistance,
            warnings,
            poiCount,
            [poi in poiDetails | {
            poi_type: poi.type,
            x: poi.location.x,
            y: poi.location.y 
            }] as poiDetail;
                """
            result = session.run(query, loc = location, des = destination)
            record = result.single()
            

            return {"path":record["path"],
                    "routeQuality": record["routeQuality"],
                    "totalDistance": record["totalDistance"],
                    "warnings": record["warnings"],
                    "poiCount":record["poiCount"],
                    "poiDetail":record["poiDetail"]}

    except Exception as e:
        print("error3")
        return {"error": "Route nicht gefunden!!!"}

    finally:
        driver.close()

#for finding route with surface and bench, and without toilet and shelter
def route_toilet_shelter (location: str, destination: str):
    
    try:
        with driver.session(database="kiss-new2") as session:
            query =  """
            MATCH (a:Address)-[:NEAREST_INTERSECTION]->(start:Point)
            WHERE a.full_address CONTAINS $loc
            MATCH (b:Address)-[:NEAREST_INTERSECTION]->(end:Point)
            WHERE b.full_address CONTAINS $des
            
            CALL org.kiss.flexibleWeightedShortestPath(
            elementId(start),
            elementId(end),
            "x", "y",
            [
            { name: "flach", maxSlope: 3.0, upWeight: 1.0, downWeight: 1.0 },
            { name: "mittel", maxSlope: 7.0, upWeight: 1.5, downWeight: 1.2 },
            { name: "steil", maxSlope: 12.0, upWeight: 2.0, downWeight: 1.4 }
            ],
            {surface: { asphalt: 1.0, gravel: 2.0, grass: 2.5}},
            { highway: ["steps"] },
            {
            bench: { maxDistance: 100.0, maxInterval: 500.0, importance: 1.5 }
            }
            )
            YIELD path, totalDistance, weightedDistance, poiCount, poiDetails, warnings, routeQuality
            RETURN
            path,
            routeQuality,
            totalDistance,
            warnings,
            poiCount,
            [poi in poiDetails | {
            poi_type: poi.type,
            x: poi.location.x,
            y: poi.location.y 
            }] as poiDetail;
                """
            result = session.run(query, loc = location, des = destination)
            record = result.single()
            

            return {"path":record["path"],
                    "routeQuality": record["routeQuality"],
                    "totalDistance": record["totalDistance"],
                    "warnings": record["warnings"],
                    "poiCount":record["poiCount"],
                    "poiDetail":record["poiDetail"]}

    except Exception as e:
        print("error3")
        return {"error": "Route nicht gefunden!!!"}

    finally:
        driver.close()
