import json
from neo4j import GraphDatabase

def sanitize_key(key):
    """Sanitize the property key to be valid in Cypher by replacing special characters."""
    return key.replace(':', '_').replace('-', '_').replace('@', '')

def load_geojson_to_neo4j(uri, user, password, geojson_path):
    # Load the GeoJSON data from the file
    with open(geojson_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    
    driver = GraphDatabase.driver(uri, auth=(user, password))
    with driver.session() as session:
        # Process each LineString feature
        for feature in data['features']:
            if feature['geometry']['type'] == 'LineString':  # Only process LineStrings
                coordinates = feature['geometry']['coordinates']
                properties = feature['properties']
                feature_id = properties.get('@id')

                # Debugging: Print all properties before sanitization
                print(f"Original properties: {properties}")

                # Sanitize and convert property keys
                sanitized_properties = {sanitize_key(k): v for k, v in properties.items()}

                # Debugging: Print all properties after sanitization
                print(f"Sanitized properties: {sanitized_properties}")

                # Process the coordinates and create nodes and relationships
                previous_node = None
                for i, (longitude, latitude) in enumerate(coordinates):
                    # Use MERGE to ensure points with the same location are not duplicated
                    point_query = """
                    MERGE (p:Point {location: point({longitude: $longitude, latitude: $latitude})})
                    SET p.longitude = $longitude, p.latitude = $latitude
                    RETURN p
                    """
                    point_params = {
                        'longitude': longitude,
                        'latitude': latitude,
                    }
                    result = session.run(point_query, point_params)

                    # If there is a previous point, create a relationship between them
                    if previous_node:
                        # Extract longitude and latitude of the previous node
                        prev_lon = previous_node['p']['location'].longitude
                        prev_lat = previous_node['p']['location'].latitude

                        # Calculate the distance (length) between the two points using Neo4j's point.distance() function
                        length_query = """
                        RETURN point.distance(
                            point({longitude: $prev_lon, latitude: $prev_lat}),
                            point({longitude: $longitude, latitude: $latitude})
                        ) AS length
                        """
                        length_result = session.run(length_query, {
                            'prev_lon': prev_lon,
                            'prev_lat': prev_lat,
                            'longitude': longitude,
                            'latitude': latitude
                        })
                        length = length_result.single()["length"]

                        # Flatten the properties into individual properties for the relationship
                        props_assignment = ', '.join(f"r.{k} = ${k}" for k in sanitized_properties.keys())
                        relation_query = f"""
                        MATCH (start:Point {{location: point({{longitude: $start_lon, latitude: $start_lat}})}}),
                              (end:Point {{location: point({{longitude: $end_lon, latitude: $end_lat}})}})
                        CREATE (start)-[r:NEXT {{id: $id, length: $length}}]->(end)
                        SET {props_assignment}
                        """
                        relation_params = {
                            'start_lon': prev_lon,
                            'start_lat': prev_lat,
                            'end_lon': longitude,
                            'end_lat': latitude,
                            'id': feature_id,
                            'length': length,  # Store the calculated length as a property
                            **sanitized_properties  # Flattened properties into individual parameters
                        }
                        session.run(relation_query, relation_params)

                    # Update the previous node for the next iteration
                    previous_node = result.single()

    driver.close()

# Usage: provide the directory of your GeoJSON file
geojson_file = r'Updated_OSM_Mülheim.geojson'
load_geojson_to_neo4j('bolt://localhost:7689', 'neo4j', 'kissthekiss', geojson_file)