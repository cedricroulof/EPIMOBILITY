import { useState } from 'react';
import { TextInput, View } from 'react-native';

export default function SearchBar({ onSearch }: { onSearch: (q: string) => void }) {
  const [query, setQuery] = useState('');

  return (
    <View style={{ margin: 16 }}>
      <TextInput
        value={query}
        onChangeText={setQuery}
        placeholder="Search a place..."
        returnKeyType="search"
        onSubmitEditing={() => onSearch(query)}
        clearButtonMode="while-editing"
        style={{
          height: 44,
          paddingHorizontal: 14,
          borderRadius: 12,
          backgroundColor: '#f0f0f0',
        }}
      />
    </View>
  );
}