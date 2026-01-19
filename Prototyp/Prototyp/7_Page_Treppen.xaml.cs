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
	public partial class _7_Page_Treppen : ContentPage
	{
        private string stairs = null;

        public _7_Page_Treppen ()
		{
			InitializeComponent ();
		}

        private async void OnTreppenOptionClicked(object sender, EventArgs e)
        {
            // Alle zurücksetzen
            TreppenOption1.BackgroundColor = Color.FromHex("#5B7C77");
            TreppenOption1.TextColor = Color.White;

            TreppenOption2.BackgroundColor = Color.FromHex("#5B7C77");
            TreppenOption2.TextColor = Color.White;

            // Gewähltes hervorheben
            var button = sender as Button;
            button.BackgroundColor = Color.FromHex("#1E2D2B");

            // 0-> Treppen können  in route sein, 1 -> Treppen sind nicht in route
            if (button.Text == "Ja, Treppen vermeiden.")
            {
                stairs = "1";
            }
            else
            {
                stairs = "0";
            }

            // Für Debug oder Weitergabe:
            Console.WriteLine("Treppen auf der Route: " + stairs);
            MainPage.Stairs = stairs;
            await Navigation.PushAsync(new _8_Page_Steigung());
        }

    }
}