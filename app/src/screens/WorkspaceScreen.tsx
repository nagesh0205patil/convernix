import React from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { ErrorNotice } from '../components/UI';
import { useWorkspace } from '../context/WorkspaceContext';
import { colors } from '../theme';

export function WorkspaceScreen() {
  const { numbers, loading, error, select, refresh } = useWorkspace();
  if (loading) return <SafeAreaView style={styles.safe}><View style={styles.center}><ActivityIndicator size="large" color={colors.brand}/></View></SafeAreaView>;
  return <SafeAreaView style={styles.safe}><ScrollView contentContainerStyle={styles.page}>
    <Text style={styles.kicker}>WHATSAPP WORKSPACE</Text><Text style={styles.title}>Choose a number</Text>
    <Text style={styles.copy}>Select the business number whose conversations and reporting you want to manage.</Text>
    {!!error && <ErrorNotice message={error}/>}<View style={styles.list}>{numbers.map(number => <Pressable key={number.id} onPress={() => select(number)} style={styles.card}>
      <View style={styles.icon}><Text>◉</Text></View><View style={styles.details}><Text style={styles.label}>{number.label || number.number}</Text><Text style={styles.number}>{number.number}</Text><Text style={styles.team}>{number.default_team || 'Support'} team</Text></View><Text style={styles.arrow}>›</Text>
    </Pressable>)}</View><Pressable onPress={refresh} style={styles.refresh}><Text style={styles.refreshText}>Refresh workspaces</Text></Pressable>
  </ScrollView></SafeAreaView>;
}

const styles = StyleSheet.create({
  safe:{flex:1,backgroundColor:colors.canvas}, center:{flex:1,alignItems:'center',justifyContent:'center'}, page:{flexGrow:1,justifyContent:'center',padding:22,gap:16}, kicker:{fontSize:12,fontWeight:'800',letterSpacing:1,color:colors.brand}, title:{fontSize:32,fontWeight:'800',color:colors.ink}, copy:{fontSize:16,lineHeight:23,color:colors.muted,marginBottom:8}, list:{gap:10}, card:{backgroundColor:'#fff',borderRadius:16,borderWidth:1,borderColor:colors.line,padding:16,flexDirection:'row',alignItems:'center',gap:13}, icon:{width:40,height:40,borderRadius:20,alignItems:'center',justifyContent:'center',backgroundColor:'#E4F4EC'}, details:{flex:1,gap:2}, label:{fontSize:16,fontWeight:'800',color:colors.ink}, number:{fontSize:14,color:colors.muted}, team:{fontSize:12,color:colors.brand,fontWeight:'700'}, arrow:{fontSize:29,color:colors.brand}, refresh:{alignSelf:'center',padding:10}, refreshText:{color:colors.brand,fontWeight:'800'}
});
