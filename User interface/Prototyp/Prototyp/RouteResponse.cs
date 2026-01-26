using Newtonsoft.Json;
using System;
using System.Collections.Generic;
using System.Text;

namespace Prototyp
{
    public class RouteResponse
    {
        [JsonProperty("wgs84_path")]
        public List<List<double>> Path { get; set; }

        [JsonProperty("totalDistance")]
        public double TotalDistance { get; set; }

        [JsonProperty("weightedDistance")]
        public double WeightedDistance { get; set; }

        [JsonProperty("routeQuality")]
        public string RouteQuality { get; set; }

        [JsonProperty("warnings")]
        public List<string> Warnings { get; set; }

        [JsonProperty("convertedPoiDetail")]
        public List<ConvertedPoiDetail> ConvertedPoiDetail { get; set; }
    }

    public class ConvertedPoiDetail
    {
        [JsonProperty("poi_type")]
        public string poi_type { get; set; }

        [JsonProperty("lat")]
        public double lat { get; set; }

        [JsonProperty("lon")]
        public double lon { get; set; }
    }
}