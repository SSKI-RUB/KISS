using System;
using System.Net.Http;
using System.Net.Security;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;

namespace Prototyp
{
    public class CustomCertificateHandler : HttpClientHandler
    {
        private const string AllowedHost = "mte-kiss.hs-ruhrwest.de";

        // SHA-256 Fingerprint aus deinem Zertifikat (ohne Leerzeichen)
        private const string AllowedFingerprint = "B3AC3F1D93358A4165E4D3EA559BAE6BA2958854881152DF08DEDD553AAFF608";

        public CustomCertificateHandler()
        {
            ServerCertificateCustomValidationCallback = (request, cert, chain, errors) =>
            {
                try
                {
                    if (request?.RequestUri?.Host == AllowedHost && cert != null)
                    {
                        var x509 = cert as X509Certificate2 ?? new X509Certificate2(cert);

                        // 👉 SHA-256 über das rohe Zertifikat berechnen
                        using (var sha256 = SHA256.Create())
                        {
                            var hash = sha256.ComputeHash(x509.RawData);
                            var thumb = BitConverter.ToString(hash)
                                                    .Replace("-", "")
                                                    .ToUpperInvariant();

                            if (thumb == AllowedFingerprint)
                            {
                                // exakt dieses Zertifikat akzeptieren (auch wenn abgelaufen)
                                return true;
                            }
                        }
                    }

                    // Standard-SSL-Prüfung für alles andere
                    return errors == SslPolicyErrors.None;
                }
                catch
                {
                    return false;
                }
            };
        }
    }
}
