import { Text, View } from 'react-native';
import MapView, { Marker } from 'react-native-maps';
import SearchBar from '../components/SearchBar';

const PLACES = [
  { id: 'fr', name: 'Paris, France', latitude: 48.8566, longitude: 2.3522 },
  { id: 'kr', name: 'Seoul, South Korea', latitude: 37.5665, longitude: 126.978 },
  { id: 'us', name: 'Los Angeles, USA', latitude: 34.0522, longitude: -118.2437 },
  { id: 'cn', name: 'Beijing, China', latitude: 39.9042, longitude: 116.4074 },
  { id: 'jp', name: 'Tokyo, Japan', latitude: 35.6762, longitude: 139.6503 },
];

function DisplayMap() {
  return (
  <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
  <View style={{ width: '90%', height: 300, borderRadius: 16, overflow: 'hidden' }}>
    <MapView style={{ flex: 1 }}>
      {PLACES.map(p => (
        <Marker key={p.id} coordinate={{ latitude: p.latitude, longitude: p.longitude }} title={p.name} />
      ))}
    </MapView>
  </View>
</View>
  );
}

export default function ExploreScreen() {
  return (
    <View style={{ flex: 1 }}>
      <SearchBar onSearch={q => console.log('search:', q)} />
      <DisplayMap />
    </View>
  );
}