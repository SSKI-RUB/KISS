using System;
using Xamarin.Forms;
using Xamarin.Forms.Xaml;

namespace Prototyp
{
    public partial class App : Application
    {
        public App()
        {
            InitializeComponent();

            MainPage = new NavigationPage(new _3_Page_Strassenbeschaffenheit())
            {
                BarBackgroundColor = Color.White, 
                BarTextColor = Color.FromHex("#222222")
            };

        }

        protected override void OnStart()
        {
        }

        protected override void OnSleep()
        {
        }

        protected override void OnResume()
        {
        }
    }
}
