using Android.Media;
using Xamarin.Forms;
using Prototyp.Droid.Services;
using Prototyp.Services;

// Alias auf die Android-Resource-Klasse:
using AndroidResource = Prototyp.Droid.Resource;

[assembly: Dependency(typeof(AudioService))]
namespace Prototyp.Droid.Services
{
    public class AudioService : IAudioService, System.IDisposable
    {
        private MediaPlayer _playerStart;
        private MediaPlayer _playerZiel;
        private MediaPlayer _playerNavStart;
        private MediaPlayer _playerNavEnd;

        public AudioService()
        {
            var ctx = Android.App.Application.Context;

            _playerStart = MediaPlayer.Create(ctx, AndroidResource.Raw.start_confirm);
            _playerZiel = MediaPlayer.Create(ctx, AndroidResource.Raw.ziel_confirm);
            _playerNavStart = MediaPlayer.Create(ctx, AndroidResource.Raw.navigation_start);
            _playerNavEnd = MediaPlayer.Create(ctx, AndroidResource.Raw.navigation_end);
        }

        public void Play(SoundType type)
        {
            switch (type)
            {
                case SoundType.StartSelected:
                    _playerStart?.SeekTo(0);
                    _playerStart?.Start();
                    break;
                case SoundType.ZielSelected:
                    _playerZiel?.SeekTo(0);
                    _playerZiel?.Start();
                    break;
                case SoundType.Navigation_Start:
                    _playerNavStart?.SeekTo(0);
                    _playerNavStart?.Start();
                    break;
                case SoundType.Navigation_End:
                    _playerNavEnd?.SeekTo(0);
                    _playerNavEnd?.Start();
                    break;
            }
        }

        public void Dispose()
        {
            _playerStart?.Release();
            _playerZiel?.Release();
            _playerNavStart?.Release();
            _playerNavEnd?.Release();
            _playerStart = null;
            _playerZiel = null;
            _playerNavStart = null;
            _playerNavEnd = null;

        }
    }
}
