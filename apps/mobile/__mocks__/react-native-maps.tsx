import { Component } from 'react';
import { View } from 'react-native';

// Native map doesn't exist under Jest; render plain views and stub the camera methods.
export default class MapView extends Component<any> {
  fitToCoordinates = () => {};
  animateToRegion = () => {};
  render() {
    return <View {...this.props} />;
  }
}
export const Marker = (props: any) => <View {...props} />;
