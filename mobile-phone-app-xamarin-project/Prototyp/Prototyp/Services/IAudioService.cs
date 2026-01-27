using System;
using System.Collections.Generic;
using System.Text;

namespace Prototyp.Services
{
    public enum SoundType
    {
        StartSelected,
        ZielSelected,
        Navigation_Start,
        Navigation_End
    }

    public interface IAudioService
    {
        void Play(SoundType type);
    }
}