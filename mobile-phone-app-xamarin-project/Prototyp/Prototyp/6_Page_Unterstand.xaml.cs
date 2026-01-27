using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

using Xamarin.Forms;
using Xamarin.Forms.Xaml;

namespace Prototyp
{
    [XamlCompilation(XamlCompilationOptions.Compile)]
    public partial class _6_Page_Unterstand : ContentPage
    {
        private string shelter = null;

        public _6_Page_Unterstand()
        {
            InitializeComponent();
        }

        private async void OnShelterOptionClicked(object sender, EventArgs e)
        {
            // Alle zurücksetzen
            ShelterOption1.BackgroundColor = Color.FromHex("#5B7C77");
            ShelterOption1.TextColor = Color.White;

            ShelterOption2.BackgroundColor = Color.FromHex("#5B7C77");
            ShelterOption2.TextColor = Color.White;

            // Gewähltes hervorheben
            var button = sender as Button;
            button.BackgroundColor = Color.FromHex("#1E2D2B");

            //1 -> Elemente sind in Route, 0->  Facilities/Hilfe können nicht in Route sein
            if (button.Text == "Ja, ich brauche unterwegs Unterstände.")
            {
                shelter = "1";
            }
            else
            {
                shelter = "0";
            }

            // Für Debug oder Weitergabe:
            Console.WriteLine("Unterstaende auf der Route: " + shelter);
            MainPage.Shelter = shelter;
            await Navigation.PushAsync(new _7_Page_Treppen());
        }
    }
}