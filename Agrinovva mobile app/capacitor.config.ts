import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.naijaharvest.app',
  appName: 'PlantDiag',
  webDir: 'src',
  android: {
    allowMixedContent: false
  },
  server: {
    androidScheme: 'https'
  }
};

export default config;