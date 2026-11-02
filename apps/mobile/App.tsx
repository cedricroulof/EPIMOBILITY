import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import ExploreScreen from './src/screens/ExploreScreen';
import WishlistScreen from './src/screens/WishlistScreen';
import ResultScreen from './src/screens/ResultScreen';
import ProfileScreen from './src/screens/ProfileScreen';
import { Globe, PasteClipboard, CheckCircle, User} from 'iconoir-react-native';


const Tab = createBottomTabNavigator();

export default function App() {
  return (
    <NavigationContainer>
      <Tab.Navigator>
        <Tab.Screen name="Explore" component={ExploreScreen} options={{ tabBarIcon: ({ color, size }) => <Globe color={color} width={size} height={size} /> }}/>
        <Tab.Screen name="Wishlist" component={WishlistScreen} options={{ tabBarIcon: ({color, size}) => <PasteClipboard color={color} width={size} height={size} />}}/>
        <Tab.Screen name="Result" component={ResultScreen} options={{ tabBarIcon: ({color, size}) => <CheckCircle color={color} width={size} height={size} /> }} />
        <Tab.Screen name="Profile" component={ProfileScreen} options={{ tabBarIcon: ({color, size}) => <User color={color} width={size} height={size} /> }} />
      </Tab.Navigator>
    </NavigationContainer>
  );
}
