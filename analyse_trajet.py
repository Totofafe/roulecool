#!/usr/bin/env python3
"""
Analyse trajet Sensor Logger - RouleCool
Compatible avec le format JSON exporté depuis Android
"""

import json
import pandas as pd
import folium
import numpy as np
from datetime import datetime
import os
import sys
import glob

# ── SEUILS DE CONFORT ────────────────────────────────────
# Modifier uniquement ce bloc pour recalibrer l'échelle.
# Après modification, mettre à jour seuils.js (même valeurs),
# vider la table Grist et ré-importer les trajets existants.
SEUILS = {
    'confortable': 5.0,   # vibration < 5.0  → Confortable
    'acceptable':  8.5,   # vibration < 8.5  → Acceptable
                          # vibration >= 8.5 → Inconfortable
    'couleurs': {
        'Confortable':   '#2E7D32',  # vert foncé
        'Acceptable':    '#A5D6A7',  # vert clair
        'Inconfortable': '#F44336',  # rouge
    }
}

def load_sensor_logger_json(json_file):
    """
    Charge le fichier JSON de Sensor Logger (format liste)
    """
    print(f"📂 Chargement de {json_file}...")
    
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Séparer par type de capteur
    accelerometer_data = []
    location_data = []
    
    for entry in data:
        sensor_type = entry.get('sensor', '')
        
        if sensor_type == 'Accelerometer':
            accelerometer_data.append({
                'time': float(entry['time']) / 1e9,  # Nanosecondes -> secondes
                'seconds': float(entry['seconds_elapsed']),
                'x': float(entry['x']),
                'y': float(entry['y']),
                'z': float(entry['z'])
            })
        
        elif sensor_type == 'Location':
            location_data.append({
                'time': float(entry['time']) / 1e9,
                'seconds': float(entry['seconds_elapsed']),
                'latitude': float(entry['latitude']),
                'longitude': float(entry['longitude']),
                'speed': float(entry.get('speed', 0)),
                'accuracy': float(entry.get('horizontalAccuracy', 0))
            })
    
    df_accel = pd.DataFrame(accelerometer_data)
    df_gps = pd.DataFrame(location_data)
    
    print(f"✅ {len(df_accel)} points accéléromètre")
    print(f"✅ {len(df_gps)} points GPS")
    
    return df_accel, df_gps

def merge_sensor_data(df_accel, df_gps):
    """
    Fusionne GPS et accéléromètre par timestamp
    """
    print("🔗 Fusion des données...")
    
    # Pour chaque point GPS, trouver l'accéléromètre le plus proche
    merged_data = []
    
    for idx, gps_row in df_gps.iterrows():
        # Trouver accéléromètre avec timestamp le plus proche
        time_diff = abs(df_accel['time'] - gps_row['time'])
        closest_idx = time_diff.idxmin()
        accel_row = df_accel.loc[closest_idx]
        
        # Calculer magnitude (norme du vecteur accélération)
        magnitude = np.sqrt(
            accel_row['x']**2 + 
            accel_row['y']**2 + 
            accel_row['z']**2
        )
        
        # Vibration = écart par rapport à la gravité terrestre
        vibration = abs(magnitude - 9.81)
        
        merged_data.append({
            'latitude': gps_row['latitude'],
            'longitude': gps_row['longitude'],
            'speed': gps_row['speed'],
            'accuracy': gps_row['accuracy'],
            'magnitude': magnitude,
            'vibration': vibration,
            'accel_x': accel_row['x'],
            'accel_y': accel_row['y'],
            'accel_z': accel_row['z'],
            'time': gps_row['time']
        })
    
    df_merged = pd.DataFrame(merged_data)
    print(f"✅ {len(df_merged)} points fusionnés")
    
    return df_merged

def calculate_comfort_score(vibration):
    """
    Convertit vibration (m/s²) en score de confort sur 3 niveaux.
    Seuils définis dans le bloc SEUILS en haut du fichier.
    """
    if vibration < SEUILS['confortable']:
        return 'Confortable'
    elif vibration < SEUILS['acceptable']:
        return 'Acceptable'
    else:
        return 'Inconfortable'

def get_color_from_score(score):
    """Couleur selon niveau de confort (définie dans SEUILS)."""
    return SEUILS['couleurs'].get(score, '#9E9E9E')

def create_map(df, output_file='trajet_confort.html'):
    """
    Crée carte interactive Folium avec segments colorés
    """
    if len(df) < 2:
        print("⚠️ Pas assez de points pour créer une carte")
        return None
    
    print("🗺️ Création de la carte interactive...")
    
    # Calculer scores
    df['score'] = df['vibration'].apply(calculate_comfort_score)
    df['color'] = df['score'].apply(get_color_from_score)
    
    # Centrer carte sur trajet
    center_lat = df['latitude'].mean()
    center_lon = df['longitude'].mean()
    
    # Créer carte
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=17,  # Zoom élevé pour trajet court
        tiles='OpenStreetMap'
    )
    
    # Ajouter segments colorés
    print(f"🎨 Ajout de {len(df)-1} segments...")
    for i in range(len(df) - 1):
        p1 = df.iloc[i]
        p2 = df.iloc[i + 1]
        
        folium.PolyLine(
            locations=[
                [p1['latitude'], p1['longitude']],
                [p2['latitude'], p2['longitude']]
            ],
            color=p1['color'],
            weight=8,
            opacity=0.85,
            popup=folium.Popup(f"""
                <div style="font-family: Arial; font-size: 12px;">
                    <b>{p1['score']}</b><br>
                    <hr style="margin: 5px 0;">
                    Vibration : <b>{p1['vibration']:.2f} m/s²</b><br>
                    Magnitude : {p1['magnitude']:.2f} m/s²<br>
                    <br>
                    <i>Accélération :</i><br>
                    • X: {p1['accel_x']:.2f}<br>
                    • Y: {p1['accel_y']:.2f}<br>
                    • Z: {p1['accel_z']:.2f}<br>
                    <br>
                    Vitesse : {p1['speed']*3.6:.1f} km/h<br>
                    Précision GPS : {p1['accuracy']:.1f} m
                </div>
            """, max_width=250)
        ).add_to(m)
    
    # Marqueurs départ/arrivée
    folium.Marker(
        [df.iloc[0]['latitude'], df.iloc[0]['longitude']],
        popup='<b>🚴 Départ</b>',
        icon=folium.Icon(color='green', icon='play', prefix='fa')
    ).add_to(m)
    
    folium.Marker(
        [df.iloc[-1]['latitude'], df.iloc[-1]['longitude']],
        popup='<b>🏁 Arrivée</b>',
        icon=folium.Icon(color='red', icon='stop', prefix='fa')
    ).add_to(m)
    
    # Légende
    legend_html = '''
    <div style="position: fixed; 
                top: 10px; right: 10px; 
                width: 220px;
                background-color: white;
                border: 2px solid grey;
                border-radius: 8px;
                padding: 15px;
                font-family: Arial;
                font-size: 13px;
                z-index: 9999;
                box-shadow: 3px 3px 10px rgba(0,0,0,0.3);">
        <h4 style="margin: 0 0 10px 0; color: #333;">🎯 RouleCool</h4>
        <div style="font-size: 11px; color: #666; margin-bottom: 10px;">
            Confort de la chaussée
        </div>
        <div style="line-height: 26px;">
            <span style="color: #2E7D32; font-size: 16px;">●</span> Confortable<br>
            <span style="color: #A5D6A7; font-size: 16px;">●</span> Acceptable<br>
            <span style="color: #F44336; font-size: 16px;">●</span> Inconfortable
        </div>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))
    
    # Sauvegarder
    m.save(output_file)
    print(f"✅ Carte sauvegardée : {output_file}")
    
    # Statistiques
    print(f"\n" + "="*50)
    print(f"📊 STATISTIQUES DU TRAJET")
    print("="*50)
    
    print(f"\n🎯 SCORES DE CONFORT")
    print(f"  Score majoritaire : {df['score'].mode()[0]}")
    confortable  = (df['score'] == 'Confortable').sum()
    acceptable   = (df['score'] == 'Acceptable').sum()
    inconfortable = (df['score'] == 'Inconfortable').sum()
    
    print(f"\n📳 VIBRATIONS")
    print(f"  Vibration moyenne : {df['vibration'].mean():.2f} m/s²")
    print(f"  Vibration max     : {df['vibration'].max():.2f} m/s²")
    print(f"  Écart-type        : {df['vibration'].std():.2f} m/s²")
    
    print(f"\n🚴 TRAJET")
    print(f"  Points GPS        : {len(df)}")
    print(f"  Vitesse moyenne   : {df['speed'].mean()*3.6:.1f} km/h")
    print(f"  Vitesse max       : {df['speed'].max()*3.6:.1f} km/h")
    
    # Distance approximative
    if len(df) >= 2:
        from math import radians, sin, cos, sqrt, atan2
        
        total_dist = 0
        for i in range(len(df)-1):
            lat1, lon1 = radians(df.iloc[i]['latitude']), radians(df.iloc[i]['longitude'])
            lat2, lon2 = radians(df.iloc[i+1]['latitude']), radians(df.iloc[i+1]['longitude'])
            
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
            c = 2 * atan2(sqrt(a), sqrt(1-a))
            total_dist += 6371 * c * 1000  # Rayon Terre en km -> mètres
        
        print(f"  Distance parcourue : {total_dist:.0f} m")
    
    # Répartition
    print(f"\n🎨 RÉPARTITION CONFORT")
    total = len(df)
    print(f"  🟢 Confortable   : {confortable:3d} pts ({100*confortable/total:5.1f}%)")
    print(f"  🟩 Acceptable    : {acceptable:3d} pts ({100*acceptable/total:5.1f}%)")
    print(f"  🔴 Inconfortable : {inconfortable:3d} pts ({100*inconfortable/total:5.1f}%)")
    
    # Top 5 pires segments
    print(f"\n⚠️  TOP 5 ZONES LES PLUS INCONFORTABLES")
    worst = df.nlargest(5, 'vibration')
    for idx, row in worst.iterrows():
        print(f"  • Vibration {row['vibration']:.2f} m/s² → {row['score']}")
        print(f"    Position : {row['latitude']:.5f}, {row['longitude']:.5f}")
    
    print("="*50 + "\n")
    
    return m

def main():
    """Fonction principale"""
    print("\n" + "="*60)
    print("🚴 RouleCool - Analyse de Trajet Vélo")
    print("   Parvis de la Défense - 12 mars 2026")
    print("="*60 + "\n")
    
    # Nom du fichier
    json_file = '14_Bis-2026-03-13_07-13-19.json'
    
    if not os.path.exists(json_file):
        print(f"❌ Fichier {json_file} non trouvé")
        print(f"📁 Fichiers présents : {os.listdir('.')}")
        return
    
    # Charger données
    df_accel, df_gps = load_sensor_logger_json(json_file)
    
    if len(df_gps) == 0:
        print("❌ Aucune donnée GPS trouvée")
        return
    
    # Fusionner
    df = merge_sensor_data(df_accel, df_gps)
    
    # Filtrer points GPS invalides/trop imprécis
    df = df[df['accuracy'] < 50]  # Garder seulement précision < 50m
    
    if len(df) < 2:
        print("⚠️ Trajet trop court ou données GPS insuffisantes")
        print(f"💡 Conseil : Faites un trajet de minimum 2-3 minutes à vélo")
        return
    
    # Créer carte
    output = json_file.replace('.json', '_carte.html')
    create_map(df, output)
    
    print(f"\n🎉 TERMINÉ !")
    print(f"📂 Carte interactive : {output}")
    print(f"💡 Ouvrez ce fichier dans votre navigateur\n")

if __name__ == "__main__":
    main()