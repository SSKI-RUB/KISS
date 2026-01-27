package org.kiss;

import org.neo4j.graphdb.*;
import org.neo4j.procedure.*;

import java.util.*;
import java.util.stream.Stream;

/**
 * POI-bewusster A* Pathfinding Algorithmus für barrierefreie Routenplanung
 *
 * Dieser Algorithmus erweitert den klassischen A* um:
 * - Berücksichtigung von Steigungen und Oberflächenbeschaffenheit
 * - Integration von Points of Interest (POIs) wie Toiletten, Bänke
 * - Dynamische Gewichtung verschiedener Zugänglichkeitsfaktoren
 */
public class CompleteAStarWithPOI {

    @Context
    public Transaction tx; // Neo4j Datenbank-Transaktion

    /**
     * Ergebnis-Klasse die alle Informationen über den gefundenen Pfad enthält
     */
    public static class PathResult {
        public final List<Node> path;
        public final double totalDistance;
        public final double weightedDistance;
        public final long poiCount;
        public final List<Map<String, Object>> poiDetails;
        public final List<String> warnings;
        public final String routeQuality;  // "perfect", "good", "fallback"

        public PathResult(List<Node> path, double totalDistance, double weightedDistance,
                          long poiCount, List<Map<String, Object>> poiDetails,
                          List<String> warnings, String routeQuality) {
            this.path = path;
            this.totalDistance = totalDistance;
            this.weightedDistance = weightedDistance;
            this.poiCount = poiCount;
            this.poiDetails = poiDetails;
            this.warnings = warnings;
            this.routeQuality = routeQuality;
        }
    }

    /**
     * Klasse zur Definition von Steigungskategorien und deren Gewichtungen
     */
    public static class SlopeCategory {
        public String name;        // z.B. "flach", "mittel", "steil"
        public double maxSlope;    // Maximale Steigung für diese Kategorie (in Prozent)
        public double upWeight;    // Gewichtung für Bergauf
        public double downWeight;  // Gewichtung für Bergab
    }

    /**
     * Haupt-Prozedur für die POI-bewusste Pfadfindung
     *
     * @param startNodeId    Element-ID des Startpunkts
     * @param endNodeId      Element-ID des Zielpunkts
     * @param xProp          Name der X-Koordinaten-Eigenschaft ("x")
     * @param yProp          Name der Y-Koordinaten-Eigenschaft ("y")
     * @param slopeCategoryData  Liste der Steigungskategorien mit Gewichtungen
     * @param propertyWeights    Gewichtungen für Oberflächeneigenschaften (z.B. Kies vs Asphalt)
     * @param excludes           Auszuschließende Wege (z.B. Treppen)
     * @param poiWeights         POI-Anforderungen (welche POIs werden benötigt)
     */
    @Procedure(name = "org.kiss.flexibleWeightedShortestPath", mode = Mode.READ)
    @Description("Flexible shortest path considering slope, surface, exclusions, and POIs along the full path")
    public Stream<PathResult> flexibleWeightedShortestPath(
            @Name("startNodeId") String startNodeId,
            @Name("endNodeId") String endNodeId,
            @Name("xProp") String xProp,
            @Name("yProp") String yProp,
            @Name("slopeCategories") List<Map<String, Object>> slopeCategoryData,
            @Name("propertyWeights") Map<String, Map<String, Object>> propertyWeights,
            @Name("excludes") Map<String, List<Object>> excludes,
            @Name(value = "poiWeights", defaultValue = "{}") Map<String, Object> poiWeights
    ) {
        // 1. Neo4j Knoten aus Element-IDs laden
        Node start = tx.getNodeByElementId(startNodeId);
        Node end = tx.getNodeByElementId(endNodeId);

        // 2. Steigungskategorien aus Input-Daten parsen
        List<SlopeCategory> slopeCategories = parseSlopeCategories(slopeCategoryData);

        // 3. A* Datenstrukturen initialisieren
        PriorityQueue<NodeWrapper> openSet = new PriorityQueue<>();  // Zu untersuchende Knoten (sortiert nach f-Score)
        Map<String, NodeWrapper> nodeMap = new HashMap<>();          // Schneller Zugriff auf Knoten-Wrapper
        Set<String> closed = new HashSet<>();                       // Bereits vollständig untersuchte Knoten

        // 4. Startknoten konfigurieren
        NodeWrapper startWrapper = new NodeWrapper(start);
        startWrapper.gScore = 0;  // Kosten vom Start = 0
        startWrapper.fScore = heuristic(start, end, xProp, yProp);  // Geschätzte Gesamtkosten
        openSet.add(startWrapper);
        nodeMap.put(start.getElementId(), startWrapper);

        // 5. A* Hauptschleife
        while (!openSet.isEmpty()) {
            // Knoten mit niedrigstem f-Score auswählen
            NodeWrapper current = openSet.poll();

            // Ziel erreicht? -> Pfad rekonstruieren und zurückgeben
            if (current.node.equals(end)) {
                PathResult result = reconstructPath(current, slopeCategories, propertyWeights, poiWeights, xProp, yProp);
                return result != null ? Stream.of(result) : Stream.empty();
            }

            // Aktuellen Knoten als "vollständig untersucht" markieren
            closed.add(current.node.getElementId());

            // 6. Alle Nachbarknoten untersuchen
            for (Relationship rel : current.node.getRelationships(Direction.BOTH)) {
                Node neighbor = rel.getOtherNode(current.node);

                // Skip wenn bereits vollständig untersucht
                if (closed.contains(neighbor.getElementId())) continue;

                // Skip wenn dieser Weg ausgeschlossen ist (z.B. Treppen)
                if (isExcluded(rel, excludes)) continue;

                // 7. Kosten für dieses Segment berechnen
                double length = getDouble(rel, "length", 1.0);              // Grunddistanz
                double slope = getDouble(rel, "slope", 0.0);                // Steigung
                double slopeWeight = getWeightForSlope(slope, slopeCategories);  // Steigungsgewichtung
                double propertyWeight = getPropertyWeight(rel, propertyWeights); // Oberflächengewichtung
                double cost = length * slopeWeight * propertyWeight;        // Gesamtkosten für dieses Segment

                // 8. POIs an diesem Kreuzungspunkt finden und bewerten
                List<Map<String, Object>> pois = findAccessiblePois(neighbor, poiWeights);
                double poiBonus = calculatePOIBonus(pois, cost, poiWeights);            // Bonus für gefundene POIs
                double tentativeG = current.gScore + cost - poiBonus;       // Neue potentielle Kosten

                // 9. Prüfen ob dieser Weg zum Nachbarn besser ist
                NodeWrapper neighborWrapper = nodeMap.computeIfAbsent(neighbor.getElementId(), k -> new NodeWrapper(neighbor));
                if (tentativeG < neighborWrapper.gScore) {
                    // Besserer Weg gefunden -> Daten aktualisieren
                    neighborWrapper.gScore = tentativeG;
                    neighborWrapper.fScore = tentativeG + heuristic(neighbor, end, xProp, yProp);
                    neighborWrapper.cameFrom = current;  // Rückverfolgung für Pfadrekonstruktion
                    neighborWrapper.rel = rel;           // Beziehung für Pfadrekonstruktion

                    // POIs vom bisherigen Pfad kopieren und neue hinzufügen
                    neighborWrapper.poisAlongPath = new ArrayList<>(current.poisAlongPath);
                    neighborWrapper.poisAlongPath.addAll(pois);

                    // Duplikate entfernen (falls POI von mehreren Kreuzungen erreichbar)
                    removeDuplicatePOIs(neighborWrapper.poisAlongPath);

                    // Zur Untersuchung hinzufügen
                    openSet.add(neighborWrapper);
                }
            }
        }

        // Kein Pfad gefunden
        return Stream.empty();
    }

    /**
     * Prüft ob eine Beziehung (Straßensegment) ausgeschlossen werden soll
     * z.B. wenn sie Treppen enthält und Treppen ausgeschlossen sind
     */
    private boolean isExcluded(Relationship rel, Map<String, List<Object>> excludes) {
        for (Map.Entry<String, List<Object>> entry : excludes.entrySet()) {
            // Prüfe jede Ausschlussbedingung (z.B. highway: ["steps"])
            if (rel.hasProperty(entry.getKey()) && entry.getValue().contains(rel.getProperty(entry.getKey()))) {
                return true; // Diese Beziehung ist ausgeschlossen
            }
        }
        return false; // Beziehung ist erlaubt
    }

    /**
     * Findet alle POIs die von einer bestimmten Kreuzung aus erreichbar sind
     * Nutzt die vorher erstellten ACCESSIBLE_FROM Beziehungen
     */
    private List<Map<String, Object>> findAccessiblePois(Node intersection, Map<String, Object> poiWeights) {
        List<Map<String, Object>> accessiblePois = new ArrayList<>();

        // Wenn keine POIs gewünscht sind, sofort zurückkehren
        if (poiWeights.isEmpty()) return accessiblePois;

        // Alle POIs finden die mit ACCESSIBLE_FROM auf diese Kreuzung zeigen
        for (Relationship accessRel : intersection.getRelationships(Direction.INCOMING, RelationshipType.withName("ACCESSIBLE_FROM"))) {
            Node poi = accessRel.getStartNode();  // POI-Knoten

            // POI muss einen Typ haben
            if (!poi.hasProperty("type")) continue;
            String poiType = poi.getProperty("type").toString();

            // Nur POIs berücksichtigen die auch gewünscht sind
            if (!poiWeights.containsKey(poiType)) continue;

            // Entfernungsconstraints prüfen
            double walkDistance = getDouble(accessRel, "walk_distance", Double.MAX_VALUE);
            double maxDistance = getMaxDistanceForPOIType(poiType, poiWeights);

            if (walkDistance <= maxDistance) {
                // POI-Informationen zusammenstellen
                Map<String, Object> poiInfo = new HashMap<>();
                poiInfo.put("type", poiType);
                poiInfo.put("osm_id", poi.getProperty("osm_id", ""));
                poiInfo.put("walk_distance", walkDistance);
                poiInfo.put("intersection_id", intersection.getElementId());

                // Koordinaten hinzufügen falls verfügbar
                if (poi.hasProperty("location")) {
                    poiInfo.put("location", poi.getProperty("location"));
                }

                accessiblePois.add(poiInfo);
            }
        }

        return accessiblePois;
    }

    /**
     * Holt die maximale Gehentfernung für einen POI-Typ aus den Benutzereinstellungen
     */
    private double getMaxDistanceForPOIType(String poiType, Map<String, Object> poiWeights) {
        Object val = poiWeights.get(poiType);
        if (val instanceof Map) {
            Map<?, ?> spec = (Map<?, ?>) val;
            if (spec.get("maxDistance") instanceof Number) {
                return ((Number) spec.get("maxDistance")).doubleValue();
            }
        }
        return 100.0; // Standard: 100m maximale Gehentfernung
    }

    /**
     * Berechnet einen Bonus für gefundene POIs
     * Nähere und wichtigere POIs geben höhere Boni
     */
    private double calculatePOIBonus(List<Map<String, Object>> pois, double segmentCost, Map<String, Object> poiWeights) {
        if (pois.isEmpty()) return 0.0;

        double bonus = 0.0;
        for (Map<String, Object> poi : pois) {
            String type = poi.get("type").toString();
            double walkDistance = (Double) poi.get("walk_distance");

            // Entfernungsbonus: Nähere POIs bekommen höheren Bonus
            double distanceBonus = Math.max(0, 50.0 - walkDistance) / 50.0;

            // Typbonus: Verschiedene POI-Typen haben verschiedene Wichtigkeiten
            double typeBonus = getPOITypeValue(type, poiWeights);

            bonus += distanceBonus * typeBonus;
        }

        // Bonus begrenzen um Routenverzerrungen zu vermeiden
        return Math.min(bonus * 10.0, segmentCost * 0.3);
    }

    /**
     * Holt die Wichtigkeit eines POI-Typs aus den Benutzereinstellungen
     * Falls nicht definiert, wird ein Standard-Wert verwendet
     */
    private double getPOITypeValue(String poiType, Map<String, Object> poiWeights) {
        Object val = poiWeights.get(poiType);
        if (val instanceof Map) {
            Map<?, ?> spec = (Map<?, ?>) val;
            if (spec.get("importance") instanceof Number) {
                return ((Number) spec.get("importance")).doubleValue();
            }
        }
        return 1.0; // Standard-Wichtigkeit für unbekannte POI-Typen
    }

    /**
     * Entfernt doppelte POIs (z.B. wenn derselbe POI von mehreren Kreuzungen erreichbar ist)
     */
    private void removeDuplicatePOIs(List<Map<String, Object>> pois) {
        Set<String> seenOsmIds = new HashSet<>();
        pois.removeIf(poi -> {
            String osmId = poi.get("osm_id").toString();
            if (seenOsmIds.contains(osmId)) {
                return true; // Entfernen: Duplikat
            }
            seenOsmIds.add(osmId);
            return false; // Behalten: Einzigartig
        });
    }

    /**
     * Rekonstruiert den finalen Pfad und prüft POI-Anforderungen
     */
    private PathResult reconstructPath(NodeWrapper end, List<SlopeCategory> slopeCategories,
                                       Map<String, Map<String, Object>> weights,
                                       Map<String, Object> poiWeights, String xProp, String yProp) {
        // Pfad aufbauen (bleibt gleich)
        List<Node> path = new ArrayList<>();
        double totalDist = 0.0;
        double weightedDist = 0.0;
        NodeWrapper current = end;

        while (current != null) {
            path.add(0, current.node);
            if (current.rel != null) {
                double len = getDouble(current.rel, "length", 1.0);
                double slope = getDouble(current.rel, "slope", 0.0);
                double slopeWeight = getWeightForSlope(slope, slopeCategories);
                double propWeight = getPropertyWeight(current.rel, weights);
                totalDist += len;
                weightedDist += len * slopeWeight * propWeight;
            }
            current = current.cameFrom;
        }

        // Gestufte POI-Validierung
        List<String> warnings = new ArrayList<>();
        String routeQuality;

        if (poiWeights.isEmpty()) {
            // Keine POI-Anforderungen
            routeQuality = "perfect";
        } else {
            // Stufe 1: Perfekte Verteilung versuchen
            if (hasPerfectPOIDistribution(end.poisAlongPath, totalDist, poiWeights)) {
                routeQuality = "perfect";
            }
            // Stufe 2: Count-basierter Fallback
            else if (hasMinimumPOICount(end.poisAlongPath, totalDist, poiWeights)) {
                routeQuality = "good";
                warnings.add("POI spacing not optimal but sufficient amenities found");

                // Detaillierte Warnung pro POI-Typ
                for (String type : poiWeights.keySet()) {
                    double maxInterval = getMaxIntervalForPOIType(type, poiWeights);
                    if (maxInterval > 0) {
                        long actualCount = end.poisAlongPath.stream()
                                .mapToLong(poi -> type.equals(poi.get("type")) ? 1 : 0)
                                .sum();
                        if (actualCount > 0) {
                            warnings.add(actualCount + " " + type + "(s) found (may be clustered)");
                        }
                    }
                }
            }
            // Stufe 3: Fallback ohne POI-Anforderungen
            else {
                routeQuality = "fallback";
                warnings.add("POI requirements not met - showing best accessibility route");

                // Spezifische fehlende POIs auflisten
                for (String type : poiWeights.keySet()) {
                    double maxInterval = getMaxIntervalForPOIType(type, poiWeights);
                    if (maxInterval > 0) {
                        long actualCount = end.poisAlongPath.stream()
                                .mapToLong(poi -> type.equals(poi.get("type")) ? 1 : 0)
                                .sum();
                        long requiredCount = (long) Math.ceil(totalDist / maxInterval);

                        if (actualCount == 0) {
                            warnings.add("No " + type + "s found (needed: " + requiredCount + ")");
                        } else {
                            warnings.add("Only " + actualCount + " " + type + "(s) found (needed: " + requiredCount + ")");
                        }
                    }
                }
            }
        }

        return new PathResult(path, totalDist, weightedDist, end.poisAlongPath.size(),
                end.poisAlongPath, warnings, routeQuality);
    }

    /**
     * Stufe 1: Perfekte POI-Verteilung (echte Positionsberechnung)
     */
    private boolean hasPerfectPOIDistribution(List<Map<String, Object>> poisAlongPath,
                                              double totalDist,
                                              Map<String, Object> poiWeights) {
        for (String poiType : poiWeights.keySet()) {
            double maxInterval = getMaxIntervalForPOIType(poiType, poiWeights);
            if (maxInterval > 0) {
                if (!checkPerfectPOISpacing(poisAlongPath, poiType, maxInterval, totalDist)) {
                    return false;
                }
            }
        }
        return true;
    }

    /**
     * Stufe 2: Minimale POI-Anzahl (Count-basiert, lockerer)
     */
    private boolean hasMinimumPOICount(List<Map<String, Object>> poisAlongPath,
                                       double totalDist,
                                       Map<String, Object> poiWeights) {
        for (String poiType : poiWeights.keySet()) {
            double maxInterval = getMaxIntervalForPOIType(poiType, poiWeights);
            if (maxInterval > 0) {
                long requiredPOIs = (long) Math.ceil(totalDist / maxInterval);
                long actualPOIs = poisAlongPath.stream()
                        .mapToLong(poi -> poiType.equals(poi.get("type")) ? 1 : 0)
                        .sum();

                if (actualPOIs < requiredPOIs) {
                    return false;
                }
            }
        }
        return true;
    }

    /**
     * Perfekte Spacing-Prüfung (TODO: Später echte Positionsberechnung)
     */
    private boolean checkPerfectPOISpacing(List<Map<String, Object>> poisAlongPath,
                                           String poiType,
                                           double maxInterval,
                                           double totalDist) {
        // Erstmal vereinfacht - später mit echter Positionsberechnung
        return hasMinimumPOICount(List.of(), totalDist, Map.of(poiType, Map.of("maxInterval", maxInterval)));
    }

    /**
     * Prüft ob POI-Abstände die maximalen Intervalle einhalten
     */
    private boolean validatePOIDistribution(List<Map<String, Object>> poisAlongPath,
                                            double totalRouteDistance,
                                            Map<String, Object> poiWeights) {

        for (String poiType : poiWeights.keySet()) {
            double maxInterval = getMaxIntervalForPOIType(poiType, poiWeights);
            if (maxInterval > 0) {
                if (!checkPOISpacing(poisAlongPath, poiType, maxInterval, totalRouteDistance)) {
                    return false;
                }
            }
        }
        return true;
    }

    /**
     * Holt das maximale Intervall für einen POI-Typ
     */
    private double getMaxIntervalForPOIType(String poiType, Map<String, Object> poiWeights) {
        Object val = poiWeights.get(poiType);
        if (val instanceof Map) {
            Map<?, ?> spec = (Map<?, ?>) val;
            if (spec.get("maxInterval") instanceof Number) {
                return ((Number) spec.get("maxInterval")).doubleValue();
            }
        }
        return 0.0; // Kein Intervall-Constraint
    }

    /**
     * Prüft ob ein POI-Typ richtig verteilt ist entlang der Route
     * Vereinfachte Prüfung - erstmal ohne genaue Positionsberechnung
     */
    private boolean checkPOISpacing(List<Map<String, Object>> poisAlongPath,
                                    String poiType,
                                    double maxInterval,
                                    double totalRouteDistance) {

        // Zähle POIs dieses Typs
        long poiCount = poisAlongPath.stream()
                .mapToLong(poi -> poiType.equals(poi.get("type")) ? 1 : 0)
                .sum();

        if (poiCount == 0) {
            // Keine POIs gefunden - okay wenn Route kurz genug
            return totalRouteDistance <= maxInterval;
        }

        // Vereinfachte Prüfung: Genügend POIs für die Routenlänge?
        // Formel: brauchen mindestens ceil(routeLength / maxInterval) POIs
        long requiredPOIs = (long) Math.ceil(totalRouteDistance / maxInterval);

        return poiCount >= requiredPOIs;
    }

    /**
     * Parst Steigungskategorien aus den Eingabedaten
     */
    private List<SlopeCategory> parseSlopeCategories(List<Map<String, Object>> input) {
        List<SlopeCategory> categories = new ArrayList<>();
        for (Map<String, Object> entry : input) {
            SlopeCategory cat = new SlopeCategory();
            cat.name = (String) entry.get("name");
            cat.maxSlope = ((Number) entry.get("maxSlope")).doubleValue();
            cat.upWeight = ((Number) entry.get("upWeight")).doubleValue();
            cat.downWeight = ((Number) entry.get("downWeight")).doubleValue();
            categories.add(cat);
        }
        return categories;
    }

    /**
     * Berechnet die Gewichtung für eine bestimmte Steigung
     */
    private double getWeightForSlope(double slope, List<SlopeCategory> categories) {
        double absSlope = Math.abs(slope);
        for (SlopeCategory cat : categories) {
            if (absSlope <= cat.maxSlope) {
                return slope >= 0 ? cat.upWeight : cat.downWeight;  // Bergauf vs Bergab
            }
        }
        return 1.0; // Fallback wenn keine Kategorie passt
    }

    /**
     * Berechnet die Gewichtung für Oberflächeneigenschaften (z.B. Asphalt vs Kies)
     */
    private double getPropertyWeight(Relationship rel, Map<String, Map<String, Object>> weights) {
        double total = 1.0;
        for (Map.Entry<String, Map<String, Object>> outer : weights.entrySet()) {
            if (rel.hasProperty(outer.getKey())) {
                Object val = rel.getProperty(outer.getKey());
                Object weight = outer.getValue().get(val.toString());
                if (weight instanceof Number) total *= ((Number) weight).doubleValue();
            }
        }
        return total;
    }

    /**
     * Heuristik für A*: Geschätzte Luftlinien-Entfernung zum Ziel
     */
    private double heuristic(Node from, Node to, String xProp, String yProp) {
        double x1 = getDouble(from, xProp, 0.0);
        double y1 = getDouble(from, yProp, 0.0);
        double x2 = getDouble(to, xProp, 0.0);
        double y2 = getDouble(to, yProp, 0.0);
        return Math.hypot(x2 - x1, y2 - y1);  // Euklidische Distanz
    }

    /**
     * Sicherheits-Hilfsmethode um Double-Werte aus Knoten zu lesen
     */
    private double getDouble(Node node, String key, double def) {
        if (!node.hasProperty(key)) return def;
        Object val = node.getProperty(key);
        if (val instanceof Number) return ((Number) val).doubleValue();
        try {
            return Double.parseDouble(val.toString());
        } catch (Exception e) {
            return def; // Fallback bei Parsing-Fehlern
        }
    }

    /**
     * Sicherheits-Hilfsmethode um Double-Werte aus Beziehungen zu lesen
     */
    private double getDouble(Relationship rel, String key, double def) {
        if (!rel.hasProperty(key)) return def;
        Object val = rel.getProperty(key);
        if (val instanceof Number) return ((Number) val).doubleValue();
        try {
            return Double.parseDouble(val.toString());
        } catch (Exception e) {
            return def; // Fallback bei Parsing-Fehlern
        }
    }

    /**
     * Wrapper-Klasse für Knoten in der A* Implementierung
     * Speichert alle Daten die für die Pfadfindung benötigt werden
     */
    private static class NodeWrapper implements Comparable<NodeWrapper> {
        Node node;                                    // Der eigentliche Neo4j Knoten
        NodeWrapper cameFrom;                         // Vorgänger-Knoten für Pfadrekonstruktion
        Relationship rel;                             // Beziehung die zu diesem Knoten führt
        double gScore = Double.POSITIVE_INFINITY;     // Tatsächliche Kosten vom Start
        double fScore = Double.POSITIVE_INFINITY;     // Geschätzte Gesamtkosten (g + Heuristik)
        List<Map<String, Object>> poisAlongPath = new ArrayList<>();  // Alle POIs entlang des Pfads

        NodeWrapper(Node node) {
            this.node = node;
        }

        // Für PriorityQueue: Sortierung nach f-Score (niedrigster zuerst)
        public int compareTo(NodeWrapper o) {
            return Double.compare(this.fScore, o.fScore);
        }
    }
}