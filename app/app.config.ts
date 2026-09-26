import type { ExpoConfig, ConfigContext } from 'expo/config';

export default ({ config }: ConfigContext): ExpoConfig => ({
  ...config,
  name: process.env.APP_NAME || 'Wavely',
  slug: 'wavely-mobile',
  scheme: 'wavely',
  version: '1.0.0',
  orientation: 'portrait',
  userInterfaceStyle: 'light',
  ios: {
    supportsTablet: true,
    bundleIdentifier: process.env.IOS_BUNDLE_IDENTIFIER || 'com.wavely.mobile',
    buildNumber: '1',
    infoPlist: { NSAppTransportSecurity: { NSAllowsArbitraryLoads: false } },
  },
  android: {
    package: process.env.ANDROID_PACKAGE || 'com.wavely.mobile',
    versionCode: 1,
    adaptiveIcon: { backgroundColor: '#0F5132' },
    permissions: [],
  },
  plugins: [['expo-secure-store', { configureAndroidBackup: true }]],
  extra: { eas: { projectId: process.env.EAS_PROJECT_ID || undefined } },
});
