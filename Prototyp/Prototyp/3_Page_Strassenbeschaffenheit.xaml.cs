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
    public partial class _3_Page_Strassenbeschaffenheit : ContentPage
    {
        private string surface = null;

        public _3_Page_Strassenbeschaffenheit()
        {
            InitializeComponent();
        }

        private async void OnSurfaceOptionClicked(object sender, EventArgs e)
        {
            // Alle zurücksetzen
            SurfaceOption1.BackgroundColor = Color.FromHex("#5B7C77");
            SurfaceOption1.TextColor = Color.White;

            SurfaceOption2.BackgroundColor = Color.FromHex("#5B7C77");
            SurfaceOption2.TextColor = Color.White;

            // Gewähltes hervorheben
            var button = sender as Button;
            button.BackgroundColor = Color.FromHex("#1E2D2B");

            // 0-> Unebene Straßen können in route sein, 1 -> Unebene Straßen sind nicht in route
            if (button.Text == "Nein, damit komme ich zurecht.")
            {
                surface = "0";
            }
            else
            {
                surface = "1";
            }

            // Für Debug oder Weitergabe:
            Console.WriteLine("Straßenoberfläche eben: " + surface);

            MainPage.Road_surface = surface;
            await Navigation.PushAsync(new _4_Page_Baenke());

        }
    }
}