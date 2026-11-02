import { useEffect, useMemo, useRef, useState } from 'react';
import { FlatList, Keyboard, Pressable, Text, View } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Collapse, Expand } from 'iconoir-react-native';
import MapView, { Marker } from 'react-native-maps';
import SearchBar from '../components/SearchBar';

const PLACES = [
  { id: 'fr', name: 'Paris, France', latitude: 48.8566, longitude: 2.3522 },
  { id: 'kr', name: 'Seoul, South Korea', latitude: 37.5665, longitude: 126.978 },
  { id: 'us', name: 'Los Angeles, USA', latitude: 34.0522, longitude: -118.2437 },
  { id: 'cn', name: 'Beijing, China', latitude: 39.9042, longitude: 116.4074 },
  { id: 'jp', name: 'Tokyo, Japan', latitude: 35.6762, longitude: 139.6503 },
];

function MapListToggle({ value, onChange }: { value: 'map' | 'list'; onChange: (v: 'map' | 'list') => void }) {
  return (
    <View style={{ flexDirection: 'row', backgroundColor: '#c6c1c1', borderRadius: 12, padding: 4, marginHorizontal: 16 , marginTop: 8}}>
      {(['map', 'list'] as const).map(v => (
        <Pressable
          key={v}
          onPress={() => onChange(v)}
          accessibilityRole="button"
          accessibilityState={{ selected: value === v }}
          style={{
            flex: 1,
            paddingVertical: 10,
            borderRadius: 9,
            alignItems: 'center',
            backgroundColor: value === v ? '#fff' : 'transparent',
          }}
        >
          <Text style={{ fontWeight: value === v ? '600' : '400' }}>{v === 'map' ? 'Map' : 'List'}</Text>
        </Pressable>
      ))}
    </View>
  );
}


function DisplayMap({ expanded, onToggle, places }: { expanded: boolean; onToggle: () => void; places: typeof PLACES }) {
  const mapRef = useRef<MapView>(null);

  // Frame the visible markers whenever the filtered list changes.
  useEffect(() => {
    if (places.length) {
      mapRef.current?.fitToCoordinates(
        places.map(p => ({ latitude: p.latitude, longitude: p.longitude })),
        { edgePadding: { top: 50, right: 50, bottom: 50, left: 50 }, animated: true },
      );
    }
  }, [places]);

  return (
    <View style={{ flex: 1, alignItems: 'center' }}>
      <View
        style={
          expanded
            ? { width: '100%', flex: 1 }
            : { flex: 1, width: '90%', borderRadius: 16, overflow: 'hidden', marginTop: 10, marginBottom: 10 }
        }
      >
        <MapView ref={mapRef} style={{ flex: 1 }}>
          {places.map(p => (
            <Marker key={p.id} coordinate={{ latitude: p.latitude, longitude: p.longitude }} title={p.name} />
          ))}
        </MapView>
        <Pressable
          onPress={onToggle}
          accessibilityRole="button"
          accessibilityLabel={expanded ? 'Collapse map' : 'Expand map'}
          style={{
            position: 'absolute',
            top: 8,
            right: 8,
            width: 36,
            height: 36,
            borderRadius: 8,
            backgroundColor: 'rgba(255,255,255,0.9)',
            justifyContent: 'center',
            alignItems: 'center',
          }}
        >
          {expanded ? <Collapse width={20} height={20} color="#000" /> : <Expand width={20} height={20} color="#000" />}
        </Pressable>
      </View>
    </View>
  );
}

export default function ExploreScreen() {
  const [expanded, setExpanded] = useState(false);
  const [view, setView] = useState<'map' | 'list'>('map');
  const [query, setQuery] = useState('');
  const visible = useMemo(
    () => PLACES.filter(p => p.name.toLowerCase().includes(query.trim().toLowerCase())),
    [query],
  );
  const navigation = useNavigation();
  const insets = useSafeAreaInsets();

  // Hide the tab bar while the map is fullscreen.
  useEffect(() => {
    navigation.setOptions({ tabBarStyle: { display: expanded ? 'none' : 'flex' } });
  }, [expanded, navigation]);

  return (
    <View style={{ flex: 1, paddingTop: expanded ? 0 : insets.top }}>
      {!expanded && <SearchBar value={query} onChangeText={setQuery} />}
      {!expanded && <MapListToggle value={view} onChange={setView} />}
      {view === 'map' ? (
        <DisplayMap
          expanded={expanded}
          places={visible}
          onToggle={() => {
            Keyboard.dismiss();
            setExpanded(e => !e);
          }}
        />
      ) : (
        <FlatList
          data={visible}
          keyExtractor={p => p.id}
          contentContainerStyle={{ padding: 16 }}
          renderItem={({ item }) => <Text style={{ paddingVertical: 12, fontSize: 16 }}>{item.name}</Text>}
        />
      )}
    </View>
  );
}
