import React from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, TextInput, TextInputProps, View } from 'react-native';
import { colors } from '../theme';

export function Button({ title, onPress, loading = false, secondary = false, disabled = false }: { title: string; onPress: () => void; loading?: boolean; secondary?: boolean; disabled?: boolean }) {
  return <Pressable accessibilityRole="button" disabled={disabled || loading} onPress={onPress} style={({ pressed }) => [s.button, secondary && s.secondary, (pressed || disabled) && s.dim]}>{loading ? <ActivityIndicator color={secondary ? colors.brand : '#fff'} /> : <Text style={[s.buttonText, secondary && s.secondaryText]}>{title}</Text>}</Pressable>;
}
export function Field(props: TextInputProps & { label: string }) { return <View style={s.field}><Text style={s.label}>{props.label}</Text><TextInput placeholderTextColor="#93A19B" {...props} style={[s.input, props.multiline && s.textarea, props.style]} /></View>; }
export function Empty({ text }: { text: string }) { return <View style={s.empty}><Text style={s.emptyTitle}>Nothing here yet</Text><Text style={s.muted}>{text}</Text></View>; }
export function ErrorNotice({ message }: { message: string }) { return <View style={s.error}><Text style={s.errorText}>{message}</Text></View>; }
export function Pill({ text }: { text: string }) { return <View style={s.pill}><Text style={s.pillText}>{text.replaceAll('_', ' ')}</Text></View>; }
const s = StyleSheet.create({
  button: { minHeight: 50, borderRadius: 12, backgroundColor: colors.brand, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 18 },
  secondary: { backgroundColor: colors.brandSoft, borderWidth: 1, borderColor: '#CBE1D7' }, buttonText: { color: '#fff', fontSize: 16, fontWeight: '700' }, secondaryText: { color: colors.brandDark }, dim: { opacity: .6 },
  field: { gap: 7 }, label: { color: colors.ink, fontWeight: '600', fontSize: 14 }, input: { minHeight: 50, borderWidth: 1, borderColor: colors.line, borderRadius: 12, paddingHorizontal: 14, color: colors.ink, backgroundColor: '#fff', fontSize: 16 }, textarea: { height: 110, paddingTop: 14, textAlignVertical: 'top' },
  empty: { paddingVertical: 44, alignItems: 'center', gap: 6 }, emptyTitle: { fontWeight: '700', color: colors.ink, fontSize: 16 }, muted: { color: colors.muted, textAlign: 'center' }, error: { backgroundColor: '#FEECEB', borderRadius: 10, padding: 12 }, errorText: { color: colors.danger },
  pill: { alignSelf: 'flex-start', borderRadius: 20, backgroundColor: colors.brandSoft, paddingHorizontal: 10, paddingVertical: 5 }, pillText: { color: colors.brandDark, textTransform: 'capitalize', fontSize: 12, fontWeight: '700' },
});
export const shared = s;
