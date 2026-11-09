module.exports = {
  preset: '@react-native/jest-preset',
  transformIgnorePatterns: [
    'node_modules/(?!((jest-)?react-native|@react-native(-community)?|@react-navigation|react-native-(screens|safe-area-context|maps|svg)|iconoir-react-native)/)',
  ],
};
