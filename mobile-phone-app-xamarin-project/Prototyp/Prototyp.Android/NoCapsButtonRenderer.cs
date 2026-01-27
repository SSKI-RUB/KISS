using Android.Content;
using Xamarin.Forms;
using Xamarin.Forms.Platform.Android;
using Prototyp.Droid;
using Prototyp.Controls;


[assembly: ExportRenderer(typeof(NoCapsButton), typeof(NoCapsButtonRenderer))]
namespace Prototyp.Droid
{
    public class NoCapsButtonRenderer : ButtonRenderer
    {
        public NoCapsButtonRenderer(Context context) : base(context)
        {
        }

        protected override void OnElementChanged(ElementChangedEventArgs<Button> e)
        {
            base.OnElementChanged(e);

            if (Control != null)
            {
                Control.TransformationMethod = null; 
            }
        }
    }
}

