using Newtonsoft.Json;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;

namespace Prototyp
{
    public class GeoJsonLoader
    {
        public static List<AddressFeature> LoadAddresses()
        {
            var assembly = typeof(GeoJsonLoader).GetTypeInfo().Assembly;

            string resourcePath = assembly.GetManifestResourceNames()
                                          .FirstOrDefault(name => name.EndsWith("muelheim.geojson"));

            if (resourcePath == null)
            {
                throw new FileNotFoundException("GeoJSON-Datei nicht gefunden! Stelle sicher, dass die Datei im Projekt vorhanden ist und als 'Embedded Resource' markiert wurde.");
            }

            Stream stream = assembly.GetManifestResourceStream(resourcePath);

            if (stream == null)
            {
                throw new FileNotFoundException($"Die Ressource '{resourcePath}' konnte nicht geöffnet werden.");
            }

            var features = new List<AddressFeature>();
            using (var reader = new StreamReader(stream))
            {
                while (!reader.EndOfStream)
                {
                    string line = reader.ReadLine();
                    if (!string.IsNullOrWhiteSpace(line))
                    {
                        try
                        {
                            // JSON-Objekt aus der Zeile deserialisieren
                            var feature = JsonConvert.DeserializeObject<AddressFeature>(line);
                            features.Add(feature);
                        }
                        catch (JsonException ex)
                        {
                            System.Diagnostics.Debug.WriteLine($"Fehler beim Parsen einer Zeile: {ex.Message}");
                        }
                    }
                }
            }

            return features;
        }
    }
}
