using System;
using System.Collections.Generic;
using System.Linq;
using Xamarin.Forms;
using Xamarin.Essentials;
using ProjNet.CoordinateSystems;
using ProjNet.CoordinateSystems.Transformations;
using Newtonsoft.Json;
using System.Threading.Tasks;
using System.Net.Http;
using System.Globalization;
using System.Threading;
using Prototyp.Services;

namespace Prototyp
{
    public partial class MainPage : ContentPage
    {
        //Variablen die von der API berücksichtigt werden können
        public static string Road_surface; //Straßenbeschaffenheit
        public static string Bench; //Bänke
        public static string Toilet; //Toiletten
        public static string Shelter; //Unterstand
        public static string Stairs; //Treppen
        public static string Slope; //Steigung

        private List<AddressFeature> allAddresses;
        private List<ConvertedPoiDetail> lastPoiList = new List<ConvertedPoiDetail>();
        private System.Timers.Timer debounceTimer;
        private bool ignoreTextChanged = false;
        private const string DefaultCity = ",Mülheim an der Ruhr";
        private bool hasAskedForLocation = false;
        
        private System.Timers.Timer gpsTimer;
        private bool isLiveTrackingActive = false;
        private bool isAutoCenter = false;
        private List<List<double>> lastRoutePath;

        private ToolbarItem settingsItem;
        private CancellationTokenSource _filterCts;

        private double _lastHeading = 0; // in Grad, 0 = Norden
        private double _smoothedHeading = 0;
        private const double HeadingAlpha = 0.25; // 0..1 (kleiner = glatter)
        private bool _compassActive = false;


        private string NormalizeAddressString(string input)
        {
            return input
                .ToLowerInvariant()
                .Replace("-", " ") // Bindestriche durch Leerzeichen ersetzen
                .Replace("straße", "strasse") // Optional: Äquivalente Schreibweisen
                .Replace("ß", "ss") // falls nötig
                .Trim();
        }

        protected override void OnAppearing()
        {
            base.OnAppearing();
            allAddresses = GeoJsonLoader.LoadAddresses();

            try
            {
                if (!_compassActive && Compass.IsMonitoring == false)
                {
                    Compass.ReadingChanged += OnCompassReadingChanged;
                    // Game = hohe Frequenz, Feel free auf Default zu stellen
                    Compass.Start(SensorSpeed.Game);
                    _compassActive = true;
                }
            }
            catch (FeatureNotSupportedException) { /* Gerät ohne Kompass – ignorieren */ }
            catch { /* egal */ }
        }

        protected override void OnDisappearing()
        {
            base.OnDisappearing();
            try
            {
                if (_compassActive)
                {
                    Compass.Stop();
                    Compass.ReadingChanged -= OnCompassReadingChanged;
                    _compassActive = false;
                }
            }
            catch { /* egal */ }
        }

        private void OnCompassReadingChanged(object sender, CompassChangedEventArgs e)
        {
            var h = e.Reading.HeadingMagneticNorth;

            // kreisförmig glätten (z. B. shortest-arc)
            double delta = ((h - _smoothedHeading + 540) % 360) - 180;
            _smoothedHeading = (_smoothedHeading + HeadingAlpha * delta + 360) % 360;

            _lastHeading = _smoothedHeading;
        }

        public MainPage()
        {
            var _ = DependencyService.Get<IAudioService>(); // preload
            InitializeComponent();
            NavigationPage.SetHasBackButton(this, false);

            // ToolbarItem vorbereiten, aber noch nicht anzeigen
            settingsItem = new ToolbarItem
            {
                IconImageSource = "settings_icon.png",
                Text = "Einstellungen",
                Command = new Command(() => OnSettingsClicked(this, EventArgs.Empty))
            };

            Device.StartTimer(TimeSpan.FromMilliseconds(500), () =>
            {
                MapWebView.Source = "file:///android_asset/Leaflet.html";
                return false;
            });
            Console.WriteLine("Road_surface: " + Road_surface + " Bench: " + Bench + " Toilet: " + Toilet + " Shelter: " + Shelter + " Stairs: " + Stairs + " Slope: " + Slope);
        }

        string CleanAddress(string input)
        {
            return input?.Split(',')[0].Trim(); // alles vor dem Komma (z. B. „Hofackerstraße 7“)
        }

        private async void OnCalculateRouteClicked(object sender, EventArgs e)
        {
            DependencyService.Get<IAudioService>()?.Play(SoundType.Navigation_Start); //Sound, Bestätigungston
            if (CalculateRouteButton.Text == "Navigation abbrechen")
            {
                DependencyService.Get<IAudioService>()?.Play(SoundType.Navigation_End); //Sound, Bestätigungston
                // Navigation abbrechen
                MapWebView.Eval("clearRoutePath();");
                MapWebView.Eval("clearAllMarkers();");
                MapWebView.Eval("clearPoiMarkers();");

                AddressInputLayout.IsVisible = true;
                CalculateRouteButton.Text = "Navigation starten";
                CalculateRouteButton.BackgroundColor = Color.FromHex("#4CAF50");

                foreach (var child in PoiButtonPanel.Children)
                {
                    if (child is Button btn)
                    {
                        btn.BackgroundColor = Color.FromHex("#E0E0E0");
                        btn.TextColor = Color.Black;
                    }
                }

                PoiButtonPanel.IsVisible = false;

                // Tracking und Auto-Center deaktivieren
                isLiveTrackingActive = false;
                isAutoCenter = false;

                StopLiveTracking();
                MapWebView.Eval("setAutoCenter(false);");

                // UI "aufräumen"
                AutoCenterToggleButton.IsVisible = false;
                AutoCenterToggleButton.BackgroundColor = Color.FromHex("#4e4e4e");
                AutoCenterToggleButton.Text = "Auto Center AUS";

                ZoomToRouteButton.IsVisible = false;
                RouteInfoPanel.IsVisible = false;

                StartSearchBar.Text = string.Empty;
                ZielSearchBar.Text = string.Empty;

                // 🔹 Header leeren
                RouteHeaderLabel.Text = string.Empty;
                RouteHeader.IsVisible = false;

                return;

            }

            string startAdresse = StartSearchBar.Text?.Trim();
            string zielAdresse = ZielSearchBar.Text?.Trim();

            if (string.IsNullOrWhiteSpace(startAdresse) || string.IsNullOrWhiteSpace(zielAdresse))
            {
                await DisplayAlert("Fehler", "Bitte Start- und Zieladresse eingeben.", "OK");
                return;
            }

            if (!startAdresse.Contains(",")) startAdresse += DefaultCity;
            if (!zielAdresse.Contains(",")) zielAdresse += DefaultCity;

            RouteLoadingOverlay.IsVisible = true;

            try
            {
                var url = $"http://mte-kiss.hs-ruhrwest.de/routing/" +
                          $"{Uri.EscapeDataString(startAdresse)}/" +
                          $"{Uri.EscapeDataString(zielAdresse)}/" +
                          $"{Road_surface}/{Bench}/{Toilet}/{Shelter}/{Stairs}/{Slope}";


                string json;
                using (var client = new HttpClient { Timeout = TimeSpan.FromSeconds(15) })
                {
                    json = await client.GetStringAsync(url);
                }

                var route = JsonConvert.DeserializeObject<RouteResponse>(json);
                if (route?.Path == null || route.Path.Count == 0)
                    throw new Exception("Leere Route erhalten.");

                HandleRouteResponse(route, startAdresse, zielAdresse);
                
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine("=== ROUTING ERROR START ===");
                System.Diagnostics.Debug.WriteLine(ex.ToString());  // inkl. InnerException
                System.Diagnostics.Debug.WriteLine("=== ROUTING ERROR END ===");

                await DisplayAlert("Fehler", $"Route konnte nicht berechnet werden.\n{ex.Message}", "OK");

                AddressInputLayout.IsVisible = true;
                CalculateRouteButton.Text = "Navigation starten";
                CalculateRouteButton.BackgroundColor = Color.FromHex("#4CAF50");
            }
            finally
            {
                RouteLoadingOverlay.IsVisible = false;
            }
        }

        private AddressFeature GetCoordinatesFromAddress(string addressInput)
        {
            if (string.IsNullOrWhiteSpace(addressInput)) return null;

            string inputNormalized = NormalizeAddressString(addressInput);

            return allAddresses.FirstOrDefault(addr =>
            {
                string fullAddress = $"{addr.properties.street} {addr.properties.number}";
                string normalizedAddress = NormalizeAddressString(fullAddress);
                return normalizedAddress == inputNormalized;
            });
        }

        private CancellationTokenSource debounceCts;
        private void Debounce(Func<Task> action, int delayMilliseconds)
        {
            // Alte Aufrufe abbrechen
            debounceCts?.Cancel();
            debounceCts = new CancellationTokenSource();
            var token = debounceCts.Token;

            Device.StartTimer(TimeSpan.FromMilliseconds(delayMilliseconds), () =>
            {
                if (token.IsCancellationRequested)
                    return false; // Timer nicht erneut starten

                Device.BeginInvokeOnMainThread(async () =>
                {
                    try
                    {
                        await action();
                    }
                    catch (OperationCanceledException)
                    {
                        // Abgebrochene Tasks ignorieren
                    }
                    catch (Exception ex)
                    {
                        Console.WriteLine("⚠️ Fehler in Debounce-Aktion: " + ex.Message);
                    }
                });

                return false; // Timer nur einmal ausführen
            });

        }


        private void OnStartSearchFocused(object sender, FocusEventArgs e)
        {
            //Falls Settings offen sind: speichern und schließen
            if (SettingsOverlay.IsVisible)
            {
                OnSaveSettingsClicked(this, EventArgs.Empty);
            }

            if (!hasAskedForLocation)
            {
                hasAskedForLocation = true;
                StartSearchBar.Unfocus(); // Tastatur unterdrücken
                ShowLocationPrompt();     // Overlay anzeigen
                return;
            }

            if (!string.IsNullOrWhiteSpace(StartSearchBar.Text))
            {
                StartAddressList.IsVisible = true;
            }
        }

        private void OnZielSearchFocused(object sender, FocusEventArgs e)
        {
            //Falls Settings offen sind: speichern und schließen
            if (SettingsOverlay.IsVisible)
            {
                OnSaveSettingsClicked(this, EventArgs.Empty);
            }

            if (!string.IsNullOrWhiteSpace(ZielSearchBar.Text))
            {
                ZielAddressList.IsVisible = true; // Liste nur dann anzeigen, wenn Text vorhanden ist
            }
        }


        public static (double lat, double lng) ConvertUtmToWgs84(double easting, double northing, int zone = 32, bool isNorthernHemisphere = true)
        {
            var utm = ProjectedCoordinateSystem.WGS84_UTM(zone, isNorthernHemisphere);
            var wgs84 = GeographicCoordinateSystem.WGS84;
            var transform = new CoordinateTransformationFactory().CreateFromCoordinateSystems(utm, wgs84);

            double[] result = transform.MathTransform.Transform(new double[] { easting, northing });
            return (result[1], result[0]); // Leaflet erwartet (lat, lng)
        }

        // ------------ STARTADRESSE LOGIK ------------
        private async void OnStartAddressSelected(object sender, ItemTappedEventArgs e)
        {
            if (e.Item != null)
            {
                ignoreTextChanged = true;
                StartSearchBar.Text = e.Item.ToString();
                StartAddressList.IsVisible = false;
                StartSearchBar.Unfocus();
                DependencyService.Get<IAudioService>()?.Play(SoundType.StartSelected); //Sound, Bestätigungston

                // Hintergrund-Thread für die Berechnung starten
                await Task.Run(() =>
                {
                    AddressFeature startKoordinaten = GetCoordinatesFromAddress(e.Item.ToString());
                    if (startKoordinaten != null)
                    {
                        var (latStart, lngStart) = ConvertUtmToWgs84(
                            startKoordinaten.geometry.coordinates[0],
                            startKoordinaten.geometry.coordinates[1]
                        );

                        Device.BeginInvokeOnMainThread(() =>
                        {
                            string js = $"addStartMarker({latStart.ToString(CultureInfo.InvariantCulture)}, {lngStart.ToString(CultureInfo.InvariantCulture)});";
                            MapWebView.Eval(js);

                            // ⬇️ Nachschub-Zoom mit kleinem Delay
                            MapWebView.Eval("setTimeout(function(){ zoomToMarkers(); }, 80);");
                        });

                    }
                });

                Device.StartTimer(TimeSpan.FromMilliseconds(300), () =>
                {
                    ignoreTextChanged = false;
                    return false;
                });
            }
        }

        // ------------ ZIELADRESSE LOGIK ------------
        private async void OnZielAddressSelected(object sender, ItemTappedEventArgs e)
        {
            if (e.Item != null)
            {
                ignoreTextChanged = true;
                ZielSearchBar.Text = e.Item.ToString();
                ZielAddressList.IsVisible = false;
                ZielSearchBar.Unfocus();
                DependencyService.Get<IAudioService>()?.Play(SoundType.ZielSelected); //Sound, Bestätigungston

                // Hintergrund-Thread für die Berechnung starten
                await Task.Run(() =>
                {
                    AddressFeature zielKoordinaten = GetCoordinatesFromAddress(e.Item.ToString());
                    if (zielKoordinaten != null)
                    {
                        var (latZiel, lngZiel) = ConvertUtmToWgs84(
                            zielKoordinaten.geometry.coordinates[0],
                            zielKoordinaten.geometry.coordinates[1]
                        );

                        Device.BeginInvokeOnMainThread(() =>
                        {
                            string js = $"addZielMarker({latZiel.ToString(CultureInfo.InvariantCulture)}, {lngZiel.ToString(CultureInfo.InvariantCulture)});";
                            MapWebView.Eval(js);
                            MapWebView.Eval("setTimeout(function(){ zoomToMarkers(); }, 80);");
                        });


                    }
                });

                Device.StartTimer(TimeSpan.FromMilliseconds(300), () =>
                {
                    ignoreTextChanged = false;
                    return false;
                });
            }
        }

        // ------------ POI Buttons LOGIK ------------
        private void OnPoiButtonClicked(object sender, EventArgs e)
        {
            if (sender is Button clickedButton)
            {
                // POI-Typ bestimmen
                string poiType = null;
                string buttonText = clickedButton.Text;
                switch (buttonText)
                {
                    case "Toilette": poiType = "toilet"; break;
                    case "Bank": poiType = "bench"; break;
                    case "Unterstand / Schatten": poiType = "shelter"; break;
                    default: return;
                }

                bool isActivating = clickedButton.BackgroundColor == Color.FromHex("#E0E0E0");

                // Alle Buttons zurücksetzen
                foreach (var child in PoiButtonPanel.Children)
                {
                    if (child is Button btn)
                    {
                        btn.BackgroundColor = Color.FromHex("#E0E0E0");
                        btn.TextColor = Color.Black;
                    }
                }

                // Alle POIs löschen
                MapWebView.Eval("clearPoiMarkers();");

                if (isActivating)
                {
                    // Button aktivieren
                    clickedButton.BackgroundColor = Color.FromHex("#4CAF50");
                    clickedButton.TextColor = Color.White;

                    // Gewählte POIs anzeigen
                    var filtered = lastPoiList
                        .Where(p => p.poi_type == poiType)
                        .Select(p => new { lat = p.lat, lon = p.lon, poi_type = p.poi_type })
                        .ToList();

                    string poiJson = JsonConvert.SerializeObject(filtered);
                    MapWebView.Eval($"showPoiMarkers({poiJson});");
                }
            }
        }


        // ------------ Location Abfrage Popup ------------
        private void ShowLocationPrompt()
        {
            LocationPromptOverlay.IsVisible = true;
        }

        private void HideLocationPrompt()
        {
            LocationPromptOverlay.IsVisible = false;
        }

        private async void OnLocationYesClicked(object sender, EventArgs e)
        {
            LocationPromptOverlay.IsVisible = false;
            RouteLoadingOverlay.IsVisible = true;

            try
            {
                var location = await Geolocation.GetLocationAsync(new GeolocationRequest
                {
                    DesiredAccuracy = GeolocationAccuracy.High,
                    Timeout = TimeSpan.FromSeconds(10)
                });

                if (location != null)
                {
                    var nearest = await Task.Run(() => FindNearestAddress(location));

                    if (nearest != null)
                    {
                        string displayAddress = $"{nearest.Value.Address.properties.street} {nearest.Value.Address.properties.number}";
                        bool useNearest = await DisplayAlert(
                            "Adresse verwenden?",
                            $"Es wurde keine exakt passende Adresse gefunden.\nMöchten Sie die nächstgelegene Adresse verwenden?\n\n{displayAddress}",
                            "Ja", "Nein");

                        if (useNearest)
                        {
                            StartSearchBar.TextChanged -= OnAddressSearchTextChanged;
                            StartSearchBar.Text = displayAddress;
                            StartAddressList.IsVisible = false;
                            StartSearchBar.TextChanged += OnAddressSearchTextChanged;

                            var coords = nearest.Value.Address.geometry.coordinates;
                            var (lat, lng) = ConvertUtmToWgs84(coords[0], coords[1]);

                            Device.BeginInvokeOnMainThread(() =>
                            {
                                MapWebView.Eval($"addStartMarker({lat.ToString(CultureInfo.InvariantCulture)}, {lng.ToString(CultureInfo.InvariantCulture)});");
                            });
                        }
                    }
                    else
                    {
                        await DisplayAlert("Hinweis", "Keine passende Adresse gefunden.", "OK");
                    }
                }
                else
                {
                    await DisplayAlert("Fehler", "Standort konnte nicht bestimmt werden.", "OK");
                }
            }
            catch (Exception ex)
            {
                await DisplayAlert("Fehler", $"Standortbestimmung fehlgeschlagen: {ex.Message}", "OK");
            }
            finally
            {
                RouteLoadingOverlay.IsVisible = false;
            }
        }

        private void OnLocationNoClicked(object sender, EventArgs e)
        {
            LocationPromptOverlay.IsVisible = false;
            Device.BeginInvokeOnMainThread(() => StartSearchBar.Focus());
        }

        // ------------ Tracking und Map Behaviour ------------

        private void OnAutoCenterToggled(object sender, EventArgs e)
        {
            isAutoCenter = !isAutoCenter;

            MapWebView.Eval($"setAutoCenter({isAutoCenter.ToString().ToLower()});");

            AutoCenterToggleButton.BackgroundColor = isAutoCenter ? Color.FromHex("#4CAF50") : Color.FromHex("#4e4e4e");
            AutoCenterToggleButton.Text = isAutoCenter ? "Wo bin ich: AN" : "Wo bin ich: AUS";
        }

        private async void OnZoomToRouteClicked(object sender, EventArgs e)
        {
            Location currentLocation = null;

            try
            {
                currentLocation = await Geolocation.GetLocationAsync(new GeolocationRequest
                {
                    DesiredAccuracy = GeolocationAccuracy.High,
                    Timeout = TimeSpan.FromSeconds(5)
                });
            }
            catch (Exception ex)
            {
                Console.WriteLine("⚠️ Fehler bei Standortabfrage: " + ex.Message);
            }

            bool nearRoute = false;
            double distanceToRoute = double.MaxValue;

            if (currentLocation != null && lastRoutePath != null)
            {
                distanceToRoute = GetDistanceToNearestRoutePoint(currentLocation, lastRoutePath);
                nearRoute = distanceToRoute <= 100; // 100 m Toleranz
            }

            // Debug-Ausgabe
            Console.WriteLine($"📏 Abstand zur Route: {distanceToRoute:F1} m");

            if (!nearRoute)
            {
                // Auto-Center nur deaktivieren, wenn nicht nahe an Route
                isAutoCenter = false;
                MapWebView.Eval("setAutoCenter(false);");

                AutoCenterToggleButton.BackgroundColor = Color.FromHex("#4e4e4e");
                AutoCenterToggleButton.Text = "Wo bin ich: AUS";
            }

            // Auf Route zoomen
            MapWebView.Eval("zoomToRouteAndMarkers();");
        }




        // ------------ GPS Tracking ------------

        private void StartLiveTracking()
        {
            isLiveTrackingActive = true;

            Device.StartTimer(TimeSpan.FromSeconds(3), () =>
            {
                if (!isLiveTrackingActive)
                    return false;

                Device.BeginInvokeOnMainThread(async () =>
                {
                    try
                    {
                        var location = await Geolocation.GetLocationAsync(new GeolocationRequest
                        {
                            DesiredAccuracy = GeolocationAccuracy.High,
                            Timeout = TimeSpan.FromSeconds(5)
                        });

                        if (location != null)
                        {
                            Console.WriteLine($"📍 GPS-Update: {location.Latitude}, {location.Longitude}");

                            var js = $"updateUserMarker({location.Latitude.ToString(CultureInfo.InvariantCulture)}, {location.Longitude.ToString(CultureInfo.InvariantCulture)}, {_lastHeading.ToString(CultureInfo.InvariantCulture)});";
                            MapWebView.Eval(js);
                        }
                        else
                        {
                            Console.WriteLine("⚠️ Kein Standort ermittelt.");
                        }
                    }
                    catch (FeatureNotEnabledException)
                    {
                        Console.WriteLine("⚠️ GPS ist deaktiviert.");
                        await DisplayAlert("GPS deaktiviert", "Bitte aktiviere die Standortdienste.", "OK");
                        StopLiveTracking();
                    }
                    catch (Exception ex)
                    {
                        Console.WriteLine("⚠️ GPS-Fehler: " + ex.Message);
                    }
                });

                return true; // Timer weiterlaufen lassen
            });
        }

        private void StopLiveTracking()
        {
            isLiveTrackingActive = false;
        }


        // ------------ Settings Overlay ------------
        private void OnSettingsClicked(object sender, EventArgs e)
        {
            // Straßenoberfläche (immer verfügbar)
            SwitchBaustellen.IsToggled = Road_surface == "1";

            // Sitzgelegenheiten
            SwitchSitzgelegenheiten.IsToggled = Bench == "1";

            // Toiletten
            SwitchToiletten.IsToggled = Toilet == "1";

            // Unterstände
            SwitchUnterstaende.IsToggled = Shelter == "1";

            // Overlay anzeigen
            SettingsOverlay.IsVisible = true;
        }



        private void OnCancelSettingsClicked(object sender, EventArgs e)
        {
            SettingsOverlay.IsVisible = false;
        }

        private async void OnSaveSettingsClicked(object sender, EventArgs e)
        {
            Road_surface = SwitchBaustellen.IsToggled ? "1" : "0";
            Bench = SwitchSitzgelegenheiten.IsToggled ? "1" : "0";
            Toilet = SwitchToiletten.IsToggled ? "1" : "0";
            Shelter = SwitchUnterstaende.IsToggled ? "1" : "0";

            Console.WriteLine($"⚙️ Einstellungen gespeichert: Strassenbeschaffenheit={Road_surface}, Sitzgelegenheiten={Bench}, Toiletten={Toilet}, Unterstände={Shelter}");

            SettingsOverlay.IsVisible = false;

            // Wenn Navigation aktiv ist -> Route neu berechnen
            if (CalculateRouteButton.Text == "Navigation abbrechen")
            {
                await RecalculateRoute();
            }
        }






        // ------------ Hilfsfunktionen ------------

        private double HaversineDistance(double lat1, double lon1, double lat2, double lon2)
        {
            const double R = 6371000; // Erdradius in Metern
            var phi1 = Math.PI * lat1 / 180.0;
            var phi2 = Math.PI * lat2 / 180.0;
            var deltaPhi = Math.PI * (lat2 - lat1) / 180.0;
            var deltaLambda = Math.PI * (lon2 - lon1) / 180.0;

            var a = Math.Sin(deltaPhi / 2) * Math.Sin(deltaPhi / 2) +
                    Math.Cos(phi1) * Math.Cos(phi2) *
                    Math.Sin(deltaLambda / 2) * Math.Sin(deltaLambda / 2);

            var c = 2 * Math.Atan2(Math.Sqrt(a), Math.Sqrt(1 - a));

            return R * c; // in Metern
        }
        private (AddressFeature Address, double Distance)? FindNearestAddress(Location location)
        {
            if (allAddresses == null || allAddresses.Count == 0) return null;

            double minDistance = double.MaxValue;
            AddressFeature nearestAddress = null;

            foreach (var addr in allAddresses)
            {
                var (lat, lng) = ConvertUtmToWgs84(
                    addr.geometry.coordinates[0],
                    addr.geometry.coordinates[1]);

                double dist = HaversineDistance(location.Latitude, location.Longitude, lat, lng);

                if (dist < minDistance)
                {
                    minDistance = dist;
                    nearestAddress = addr;
                }
            }

            return nearestAddress != null ? (nearestAddress, minDistance) : (ValueTuple<AddressFeature, double>?)null;


        }
        private double GetDistanceToNearestRoutePoint(Location userLocation, List<List<double>> routePath)
        {
            if (routePath == null || routePath.Count == 0 || userLocation == null)
                return double.MaxValue;

            double minDistance = double.MaxValue;

            foreach (var point in routePath)
            {
                if (point.Count < 2) continue;

                double lat = point[0]; //Lat
                double lon = point[1]; //Lon

                double dist = HaversineDistance(userLocation.Latitude, userLocation.Longitude, lat, lon);

                if (dist < minDistance)
                    minDistance = dist;
            }

            return minDistance;
        }
        private void OnMapLoaded(object sender, WebNavigatedEventArgs e)
        {
            if (!ToolbarItems.Contains(settingsItem))
            {
                ToolbarItems.Add(settingsItem);
            }
        }
        private void ShowPoiMarkers(string type)
        {
            var filtered = lastPoiList
                .Where(p => p.poi_type == type)
                .Select(p => new { lat = p.lat, lon = p.lon, poi_type = p.poi_type })
                .ToList();

            string poiJson = JsonConvert.SerializeObject(filtered);
            MapWebView.Eval($"showPoiMarkers({poiJson});");
        }
        private async Task RecalculateRoute()
        {
            string startAdresse = StartSearchBar.Text?.Trim();
            string zielAdresse = ZielSearchBar.Text?.Trim();

            if (string.IsNullOrWhiteSpace(startAdresse) || string.IsNullOrWhiteSpace(zielAdresse))
                return;

            if (!startAdresse.Contains(",")) startAdresse += DefaultCity;
            if (!zielAdresse.Contains(",")) zielAdresse += DefaultCity;

            RouteLoadingOverlay.IsVisible = true;

            try
            {
                var url = $"http://mte-kiss.hs-ruhrwest.de/routing/" +
                          $"{Uri.EscapeDataString(startAdresse)}/" +
                          $"{Uri.EscapeDataString(zielAdresse)}/" +
                          $"{Road_surface}/{Bench}/{Toilet}/{Shelter}/{Stairs}/{Slope}";

                string json;
                using (var client = new HttpClient { Timeout = TimeSpan.FromSeconds(15) })
                    json = await client.GetStringAsync(url);

                var route = JsonConvert.DeserializeObject<RouteResponse>(json);
                if (route?.Path == null || route.Path.Count == 0)
                    throw new Exception("Leere Route erhalten.");

                HandleRouteResponse(route, startAdresse, zielAdresse);
            }
            catch (Exception ex)
            {
                await DisplayAlert("Fehler", $"Route konnte nicht neu berechnet werden.\n{ex.Message}", "OK");
            }
            finally
            {
                RouteLoadingOverlay.IsVisible = false;
            }
        }
        private void HandleRouteResponse(RouteResponse route, string startAdresse, string zielAdresse)
        {
            // --- Route-Infos Label füllen ---
            if (route.TotalDistance > 0)
            {
                string distanceText = route.TotalDistance >= 1000
                    ? $"{(route.TotalDistance / 1000.0):F1} km, "
                    : $"{route.TotalDistance:F0} m, ";
                RouteDistanceLabel.Text = distanceText;

                double metersPerMinute = 65.0; // seniorenfreundlich
                double durationMinutes = route.TotalDistance / metersPerMinute;
                RouteDurationLabel.Text = $"{Math.Round(durationMinutes):F0} Min.";

                RouteInfoPanel.IsVisible = true;
            }
            else
            {
                RouteInfoPanel.IsVisible = false;
            }

            // Routenpunkte & POIs merken
            lastRoutePath = route.Path;
            lastPoiList = route.ConvertedPoiDetail ?? new List<ConvertedPoiDetail>();

            int countToilets = lastPoiList.Count(p => p.poi_type == "toilet");
            int countBenches = lastPoiList.Count(p => p.poi_type == "bench");
            int countShelters = lastPoiList.Count(p => p.poi_type == "shelter");

            // Hinweise, falls gewünschte POIs fehlen
            var poiChecks = new (string type, string name, string flag, int count)[]
            {
                ("toilet", "Toiletten", Toilet, countToilets),
                ("bench", "Bänke", Bench, countBenches),
                ("shelter", "Unterstände oder Schattenplätze", Shelter, countShelters)
            };

            var notFoundList = poiChecks
                .Where(p => p.flag == "1" && p.count == 0)
                .Select(p => p.name)
                .ToList();

            if (notFoundList.Any())
            {
                string joined = string.Join(" oder ", notFoundList);
                Device.BeginInvokeOnMainThread(async () =>
                {
                    await DisplayAlert("Hinweis", $"Auf dieser Route wurden keine {joined} gefunden.", "OK");
                });
            }

            string pathJson = JsonConvert.SerializeObject(route.Path);

            Device.BeginInvokeOnMainThread(() =>
            {
                // Merken, ob wir JETZT erst in den Navigationsmodus wechseln
                bool startingNavigationNow = CalculateRouteButton.Text != "Navigation abbrechen";
                // Auto-Center nur beim ersten Start default AN, sonst Benutzerzustand beibehalten
                bool desiredAutoCenter = startingNavigationNow ? true : isAutoCenter;

                // Karte neu zeichnen
                MapWebView.Eval("clearRoutePath();");
                MapWebView.Eval("clearAllMarkers();");
                MapWebView.Eval("clearPoiMarkers();");
                MapWebView.Eval($"addRoutePath({pathJson});");

                // Start-Marker
                if (!string.IsNullOrWhiteSpace(startAdresse))
                {
                    string cleanedStart = CleanAddress(startAdresse);
                    var startFeature = GetCoordinatesFromAddress(cleanedStart);
                    if (startFeature != null)
                    {
                        var (latStart, lngStart) = ConvertUtmToWgs84(
                            startFeature.geometry.coordinates[0],
                            startFeature.geometry.coordinates[1]);
                        MapWebView.Eval($"addStartMarker({latStart.ToString(CultureInfo.InvariantCulture)}, {lngStart.ToString(CultureInfo.InvariantCulture)});");
                    }
                }

                // Ziel-Marker
                if (!string.IsNullOrWhiteSpace(zielAdresse))
                {
                    string cleanedZiel = CleanAddress(zielAdresse);
                    var zielFeature = GetCoordinatesFromAddress(cleanedZiel);
                    if (zielFeature != null)
                    {
                        var (latZiel, lngZiel) = ConvertUtmToWgs84(
                            zielFeature.geometry.coordinates[0],
                            zielFeature.geometry.coordinates[1]);
                        MapWebView.Eval($"addZielMarker({latZiel.ToString(CultureInfo.InvariantCulture)}, {lngZiel.ToString(CultureInfo.InvariantCulture)});");
                    }
                }

                // Eingabe & Buttons anpassen
                AddressInputLayout.IsVisible = false;
                CalculateRouteButton.Text = "Navigation abbrechen";
                CalculateRouteButton.BackgroundColor = Color.FromHex("#E57373");
                PoiButtonPanel.IsVisible = true;

                PoiButton1.IsVisible = Toilet == "1" && countToilets > 0;
                PoiButton2.IsVisible = Bench == "1" && countBenches > 0;
                PoiButton3.IsVisible = Shelter == "1" && countShelters > 0;

                // --- Alle POI Buttons immer resetten (auch die sichtbaren) ---
                foreach (var child in PoiButtonPanel.Children)
                {
                    if (child is Button btn)
                    {
                        btn.BackgroundColor = Color.FromHex("#E0E0E0");
                        btn.TextColor = Color.Black;
                    }
                }

                // Header
                string startKurz = StripCity(startAdresse);
                string zielKurz = StripCity(zielAdresse);
                RouteHeaderLabel.Text = $"Von: {startKurz}\nNach: {zielKurz}";
                RouteHeader.IsVisible = true;

                // Live-Tracking nur starten, wenn es noch nicht läuft
                if (!isLiveTrackingActive)
                {
                    isLiveTrackingActive = true;
                    StartLiveTracking();
                }

                // Auto-Center gemäß gewünschtem Zustand anwenden
                ApplyAutoCenterUI(desiredAutoCenter);

                ZoomToRouteButton.IsVisible = true;
                MapWebView.Eval("zoomToRouteAndMarkers();");
            });
        }
        private string StripCity(string adresse)
        {
            if (string.IsNullOrWhiteSpace(adresse)) return string.Empty;
            return adresse.Split(',')[0].Trim(); // nur der Teil vor dem ersten Komma
        }
        private void ApplyAutoCenterUI(bool state)
        {
            isAutoCenter = state;
            MapWebView.Eval($"setAutoCenter({state.ToString().ToLower()});");
            AutoCenterToggleButton.IsVisible = true;
            AutoCenterToggleButton.BackgroundColor = state ? Color.FromHex("#4CAF50") : Color.FromHex("#4e4e4e");
            AutoCenterToggleButton.Text = state ? "Wo bin ich: AN" : "Wo bin ich: AUS";
        }
        private void OnAddressSearchTextChanged(object sender, TextChangedEventArgs e)
        {
            if (ignoreTextChanged) return;

            // Route immer löschen, wenn Text geändert wird
            MapWebView.Eval("clearRoutePath();");

            if (!(sender is SearchBar searchBar)) return;

            // Welche Liste gehört dazu?
            var targetList = (searchBar == StartSearchBar) ? StartAddressList : ZielAddressList;

            if (string.IsNullOrWhiteSpace(e.NewTextValue))
            {
                targetList.IsVisible = false;
                return;
            }

            // Vorherige Filter-Tasks abbrechen
            _filterCts?.Cancel();
            _filterCts = new CancellationTokenSource();
            var token = _filterCts.Token;

            Debounce(async () =>
            {
                var localToken = token; // capture

                try
                {
                    string query = NormalizeAddressString(e.NewTextValue);

                    var filteredAddresses = await Task.Run(() =>
                    {
                        // früh raus, falls schon abgebrochen
                        if (localToken.IsCancellationRequested)
                            localToken.ThrowIfCancellationRequested();

                        var projected = allAddresses
                            .Where(a =>
                            {
                                string fullAddress = $"{a.properties.street} {a.properties.number}";
                                string normalized = NormalizeAddressString(fullAddress);
                                return normalized.Contains(query);
                            })
                            // einmalig Keys vorbereiten (spart viel Rechenzeit)
                            .Select(a => new
                            {
                                Street = a.properties.street,
                                Number = a.properties.number,
                                NormStreet = NormalizeAddressString(a.properties.street),
                                House = ParseHouseNumber(a.properties.number)
                            });

                        // sortieren + begrenzen
                        var list = projected
                            .OrderBy(x => x.NormStreet)
                            .ThenBy(x => x.House.num)
                            .ThenBy(x => x.House.suffix)
                            .Select(x => $"{x.Street} {x.Number}")
                            .Take(40) // UI klein und schnell halten
                            .ToList();

                        return list;
                    }, localToken).ConfigureAwait(false);

                    if (localToken.IsCancellationRequested) return;

                    Device.BeginInvokeOnMainThread(() =>
                    {
                        if (localToken.IsCancellationRequested) return;

                        targetList.ItemsSource = filteredAddresses;
                        targetList.IsVisible = filteredAddresses.Any();
                    });
                }
                catch (OperationCanceledException)
                {
                    // normal bei schnellem Tippen – einfach ignorieren
                }
                catch (Exception ex)
                {
                    System.Diagnostics.Debug.WriteLine("Filter-Fehler: " + ex.Message);
                }
            }, 250); // leicht kürzer, fühlt sich flotter an


        }
        private (int num, string suffix) ParseHouseNumber(string number)
        {
            if (string.IsNullOrWhiteSpace(number))
                return (int.MaxValue, "");

            // Bereich "12-14" -> nimm die erste Zahl
            var n = number.Split('-')[0].Trim();

            int i = 0;
            while (i < n.Length && char.IsDigit(n[i])) i++;

            var numPart = (i > 0) ? n.Substring(0, i) : "";
            var suffix = (i < n.Length) ? n.Substring(i).Trim().ToLowerInvariant() : "";

            if (!int.TryParse(numPart, out var num))
                num = int.MaxValue;

            return (num, suffix);
        }

    }
}
