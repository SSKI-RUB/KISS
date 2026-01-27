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
	public partial class _8_Page_Steigung : ContentPage
	{
        private string slope = null;

        public _8_Page_Steigung ()
		{
			InitializeComponent ();
		}

        private async void OnSlopeOptionClicked(object sender, EventArgs e)
        {
            // Alle zurücksetzen
            SlopeOption1.BackgroundColor = Color.FromHex("#5B7C77");
            SlopeOption1.TextColor = Color.White;

            SlopeOption2.BackgroundColor = Color.FromHex("#5B7C77");
            SlopeOption2.TextColor = Color.White;

            // Gewähltes hervorheben
            var button = sender as Button;
            button.BackgroundColor = Color.FromHex("#1E2D2B");

            // 0-> Steigungen können  in route sein, 1 -> Steigungen sind nicht in route
            if (button.Text == "Ja, ich möchte Steigungen und Bergauf vermeiden")
            {
                slope = "1";
            }
            else
            {
                slope = "0";
            }

            // Für Debug oder Weitergabe:
            Console.WriteLine("Unterstand vorhanden: " + slope);
            MainPage.Slope = slope;
            LoadingOverlay.IsVisible = true;
            await Task.Delay(100);

            try
            {
                // Navigation zur MainPage (Leaflet lädt dort im Hintergrund)
                await Navigation.PushAsync(new MainPage());
            }
            finally
            {
                // Lade-Overlay AUS, falls man per „Zurück“ wieder hier landet
                LoadingOverlay.IsVisible = false;
            }
        }
    }
}