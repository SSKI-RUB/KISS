using System;
using Xamarin.Forms;
using Xamarin.Forms.Xaml;

namespace Prototyp
{
    [XamlCompilation(XamlCompilationOptions.Compile)]
    public partial class _5_Page_Toiletten : ContentPage
    {
        private string toilet = null;

        public _5_Page_Toiletten()
        {
            InitializeComponent();
        }

        private async void OnToiletOptionClicked(object sender, EventArgs e)
        {
            // Alle zurücksetzen
            ToiletOption1.BackgroundColor = Color.FromHex("#5B7C77");
            ToiletOption1.TextColor = Color.White;

            ToiletOption2.BackgroundColor = Color.FromHex("#5B7C77");
            ToiletOption1.TextColor = Color.White;

            // Gewähltes hervorheben
            var button = sender as Button;
            button.BackgroundColor = Color.FromHex("#1E2D2B");


            if (button.Text == "Ja, ich benötige Toiletten.")
            {
                toilet = "1";
            }
            else
            {
                toilet = "0";
            }

            // Für Debug oder Weitergabe:
            Console.WriteLine("Toiletten auf der Route: " + toilet);
            MainPage.Toilet = toilet;
            await Navigation.PushAsync(new _6_Page_Unterstand());
        }
    }
}