import { TextInput, View } from 'react-native';

export default function SearchBar({ value, onChangeText }: { value: string; onChangeText: (q: string) => void }) {
  return (
    <View style={{ margin: 16 }}>
      <TextInput
        value={value} onChangeText={onChangeText}
        placeholder="Search a place..."
        returnKeyType="search"
        clearButtonMode="while-editing"
        style={{
          height: 44,
          paddingHorizontal: 14,
          borderRadius: 12,
          backgroundColor: '#f0f0f0',
            color: '#1d1616',
            fontSize: 30,
        }}
      />
    </View>
  );
}