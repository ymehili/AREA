import React, { useState, useEffect } from 'react';
import {
  SafeAreaView,
  View,
  Text,
  ActivityIndicator,
  Alert
} from 'react-native';
import { useAuth, requestJson } from '../..//App';
import { Colors } from '../constants/colors';
import { TextStyles } from '../constants/typography';
import CustomButton from './ui/Button';
import Card from './ui/Card';

type ConfirmScreenProps = {
  route?: {
    params?: {
      token?: string;
    };
  };
};

export default function ConfirmScreen({ route }: ConfirmScreenProps) {
  const auth = useAuth();
  const [loading, setLoading] = useState(true);
  const [success, setSuccess] = useState<boolean | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const token = route?.params?.token;

  useEffect(() => {
    const confirmEmail = async () => {
      if (!token) {
        setMessage('No confirmation token provided.');
        setSuccess(false);
        setLoading(false);
        return;
      }

      try {
        // Call the API to confirm the email using the requestJson function from the main app
        await requestJson(`/auth/confirm/${token}`, {
          method: 'POST',
        }, null); // No token needed for confirmation endpoint
        
        setMessage('Email confirmed successfully! You can now sign in.');
        setSuccess(true);
      } catch (error: any) {
        setMessage(error.message || 'Confirmation failed. Please try again.');
        setSuccess(false);
      } finally {
        setLoading(false);
      }
    };

    confirmEmail();
  }, [token]);

  const handleGoToLogin = () => {
    // Navigate back to login screen
    auth.logout();
  };

  if (loading) {
    return (
      <SafeAreaView style={styles.screen}>
        <View style={styles.centered}>
          <ActivityIndicator size="large" color={Colors.primary} />
          <Text style={[styles.muted, { marginTop: 16 }]}>Confirming your email...</Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.screen}>
      <View style={styles.centered}>
        <Card style={{ margin: 16, width: '90%', maxWidth: 400 }}>
          {success ? (
            <>
              <View style={{ alignItems: 'center', marginBottom: 16 }}>
                <Text style={[styles.h1, { color: Colors.success, fontSize: 24 }]}>
                  ✓
                </Text>
              </View>
              <Text style={[styles.h2, { textAlign: 'center', marginBottom: 12 }]}>
                Email Confirmed!
              </Text>
              <Text style={[styles.muted, { textAlign: 'center', marginBottom: 24 }]}>
                {message}
              </Text>
              <CustomButton
                title="Go to Login"
                onPress={handleGoToLogin}
                variant="default"
              />
            </>
          ) : (
            <>
              <View style={{ alignItems: 'center', marginBottom: 16 }}>
                <Text style={[styles.h1, { color: Colors.error, fontSize: 24 }]}>
                  ✕
                </Text>
              </View>
              <Text style={[styles.h2, { textAlign: 'center', marginBottom: 12 }]}>
                Confirmation Failed
              </Text>
              <Text style={[styles.muted, { textAlign: 'center', marginBottom: 24 }]}>
                {message}
              </Text>
              <CustomButton
                title="Try Again"
                onPress={() => window.location.reload()}
                variant="outline"
              />
            </>
          )}
        </Card>
      </View>
    </SafeAreaView>
  );
}

const styles = {
  screen: {
    flex: 1,
    backgroundColor: Colors.backgroundLight,
    padding: 16,
  },
  centered: {
    flex: 1,
    backgroundColor: Colors.backgroundLight,
    padding: 16,
    justifyContent: 'center',
  },
  h1: {
    ...TextStyles.h1,
    color: Colors.textDark,
    textAlign: 'center',
    marginBottom: 12,
  },
  h2: {
    ...TextStyles.h2,
    color: Colors.textDark,
    textAlign: 'center',
    marginBottom: 12,
  },
  muted: {
    color: Colors.mutedForeground,
    marginTop: 4,
    ...TextStyles.small,
    textAlign: 'center',
  },
};