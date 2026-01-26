using System;
using Xamarin.Forms;
using Xamarin.Forms.Xaml;

namespace Prototyp
{
    [XamlCompilation(XamlCompilationOptions.Compile)]
    public partial class _4_Page_Baenke : ContentPage
    {
        private string bench = null;

        public _4_Page_Baenke()
        {
            InitializeComponent();
        }

        private async void OnBenchOptionClicked(object sender, EventArgs e)
        {
            // Alle zurücksetzen
            BenchOption1.BackgroundColor = Color.FromHex("#5B7C77");
            BenchOption1.TextColor = Color.White;

            BenchOption2.BackgroundColor = Color.FromHex("#5B7C77");
            BenchOption2.TextColor = Color.White;

            // Gewähltes hervorheben
            var button = sender as Button;
            button.BackgroundColor = Color.FromHex("#1E2D2B");


            if (button.Text == "Ja, ich möchte mich ausruhen können.")
            {
                bench = "1";
            }
            else
            {
                bench = "0";
            }

            // Für Debug oder Weitergabe:
            Console.WriteLine("Bänke auf der Route: " + bench);
            MainPage.Bench = bench;
            await Navigation.PushAsync(new _5_Page_Toiletten());
        }
    }
}