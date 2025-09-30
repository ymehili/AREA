import * as Font from 'expo-font';
import { useEffect, useState } from 'react';

// Import Google Fonts
import {
  Inter_400Regular,
  Inter_500Medium,
  Inter_700Bold,
  useFonts as useInterFonts,
} from '@expo-google-fonts/inter';

import {
  DelaGothicOne_400Regular,
  useFonts as useDelaGothicOneFonts,
} from '@expo-google-fonts/dela-gothic-one';

import {
  RobotoMono_400Regular,
  useFonts as useRobotoMonoFonts,
} from '@expo-google-fonts/roboto-mono';

export const useAppFonts = () => {
  const [interLoaded] = useInterFonts({
    Inter_400Regular,
    Inter_500Medium,
    Inter_700Bold,
  });
  
  const [delaGothicLoaded] = useDelaGothicOneFonts({
    DelaGothicOne_400Regular,
  });
  
  const [robotoMonoLoaded] = useRobotoMonoFonts({
    RobotoMono_400Regular,
  });
  
  const [fontsLoaded, setFontsLoaded] = useState(false);
  
  useEffect(() => {
    if (interLoaded && delaGothicLoaded && robotoMonoLoaded) {
      setFontsLoaded(true);
    }
  }, [interLoaded, delaGothicLoaded, robotoMonoLoaded]);
  
  return fontsLoaded;
};