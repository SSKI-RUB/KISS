using System.Collections.Generic;

namespace Prototyp
{

    public class AddressFeature
    {
        public AddressProperties properties { get; set; }
        public AddressGeometry geometry { get; set; }
    }

    public class AddressProperties
    {
        public string hash { get; set; }
        public string number { get; set; }
        public string street { get; set; }
        public string unit { get; set; }
        public string city { get; set; }
        public string district { get; set; }
        public string region { get; set; }
        public string postcode { get; set; }
        public string id { get; set; }
    }

    public class AddressGeometry
    {
        public string type { get; set; }
        public double[] coordinates { get; set; } // X (Ost), Y (Nord)
    }

    public class AddressCollection
    {
        public List<AddressFeature> features { get; set; }
    }
}
