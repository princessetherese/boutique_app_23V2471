# app_supabase_sync.py - Version avec synchronisation Supabase
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression
from sklearn.cluster import KMeans
from sklearn.metrics import r2_score, silhouette_score
import time
import warnings
warnings.filterwarnings('ignore')

# ==================== CONFIGURATION SUPABASE ====================
SUPABASE_URL = "https://lojxytucxpxvxvqdelue.supabase.co"
SUPABASE_ANON_KEY = "sb_publishable_dABCJ88o2IvCZTrPHpuR3g_A0zl6Q57"

try:
    from supabase import create_client, Client
    supabase_available = True
except ImportError:
    supabase_available = False
    st.warning("⚠️ Supabase non installé. Installation: pip install supabase")

def init_supabase():
    if supabase_available:
        return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    return None

# ==================== FONCTIONS SUPABASE ====================
def save_client_to_supabase(supabase, client_data):
    """Sauvegarde un client dans Supabase"""
    try:
        data = {
            'client_id': int(client_data['client_id']),
            'nom': client_data['nom'],
            'email': client_data['email'],
            'age': int(client_data['âge']),
            'ville': client_data['ville'],
            'revenu_annuel_fcfa': int(client_data['revenu_annuel_fcfa']),
            'ca_total_fcfa': int(client_data['ca_total_fcfa']),
            'nb_achats': int(client_data['nb_achats'])
        }
        supabase.table('clients').upsert(data).execute()
        return True
    except Exception as e:
        return False

def save_order_to_supabase(supabase, order_data):
    """Sauvegarde une commande dans Supabase"""
    try:
        data = {
            'date': order_data['date'].isoformat() if hasattr(order_data['date'], 'isoformat') else order_data['date'],
            'client_id': int(order_data['client_id']),
            'produits': ','.join(order_data['produits']),
            'montant_fcfa': int(order_data['montant_fcfa']),
            'mode_paiement': order_data['mode_paiement'],
            'nb_articles': int(order_data['nb_articles'])
        }
        supabase.table('commandes').insert(data).execute()
        return True
    except Exception as e:
        print(f"Erreur: {e}")
        return False

def load_all_clients_from_supabase(supabase):
    """Charge tous les clients depuis Supabase"""
    try:
        result = supabase.table('clients').select('*').execute()
        if result.data:
            df = pd.DataFrame(result.data)
            df = df.rename(columns={
                'age': 'âge',
                'client_id': 'client_id',
                'nom': 'nom',
                'email': 'email',
                'ville': 'ville',
                'revenu_annuel_fcfa': 'revenu_annuel_fcfa',
                'ca_total_fcfa': 'ca_total_fcfa',
                'nb_achats': 'nb_achats'
            })
            return df
        return None
    except:
        return None

def load_all_orders_from_supabase(supabase):
    """Charge toutes les commandes depuis Supabase"""
    try:
        result = supabase.table('commandes').select('*').order('date', desc=True).execute()
        if result.data:
            orders = []
            for item in result.data:
                orders.append({
                    'date': pd.to_datetime(item['date']),
                    'client_id': item['client_id'],
                    'produits': item['produits'].split(','),
                    'montant_fcfa': item['montant_fcfa'],
                    'mode_paiement': item['mode_paiement'],
                    'nb_articles': item['nb_articles']
                })
            return orders
        return None
    except:
        return None

def sync_all_to_supabase(supabase, df_clients, historique_achats):
    """Synchronise toutes les données vers Supabase"""
    if not supabase:
        return 0, 0
    
    clients_saved = 0
    orders_saved = 0
    
    # Sauvegarde des clients
    for _, client in df_clients.iterrows():
        if save_client_to_supabase(supabase, client.to_dict()):
            clients_saved += 1
    
    # Sauvegarde des commandes
    for order in historique_achats:
        if save_order_to_supabase(supabase, order):
            orders_saved += 1
    
    return clients_saved, orders_saved

# ==================== CONFIGURATION ====================
st.set_page_config(
    page_title="ShopAnalyzer - Armelle",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="auto"
)

# ==================== CSS - INTERFACE BLANCHE ====================
st.markdown("""
<!-- Font Awesome 6 CDN -->
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
<style>
    * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }
    
    .stApp, .main, .st-bw, .st-cf, .st-ae, .st-af {
        background-color: #ffffff !important;
    }
    
    .stApp {
        background-color: #ffffff;
    }
    
    .main > div, .block-container {
        background-color: #ffffff;
    }
    
    :root {
        --primary: #667eea;
        --primary-dark: #5a67d8;
        --secondary: #764ba2;
        --success: #48bb78;
        --danger: #f56565;
        --warning: #ed8936;
    }
    
    .main-header {
        background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
        padding: clamp(1rem, 5vw, 2rem);
        border-radius: clamp(10px, 3vw, 20px);
        margin-bottom: clamp(1rem, 4vw, 2rem);
        color: white;
        text-align: center;
    }
    
    .main-header h1 {
        font-size: clamp(1.5rem, 6vw, 2.5rem);
        margin: 0;
    }
    
    .main-header p {
        font-size: clamp(0.8rem, 3vw, 1rem);
        margin-top: 0.5rem;
        opacity: 0.9;
    }
    
    .metric-card {
        background: #ffffff;
        padding: clamp(0.8rem, 3vw, 1.2rem);
        border-radius: clamp(10px, 3vw, 15px);
        text-align: center;
        transition: transform 0.3s ease;
        border: 1px solid #e2e8f0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.1);
    }
    
    .metric-value {
        font-size: clamp(1.2rem, 4vw, 1.8rem);
        font-weight: 700;
        color: var(--primary);
        margin: 0.5rem 0;
    }
    
    .metric-label {
        font-size: clamp(0.7rem, 2.5vw, 0.85rem);
        color: #6c757d;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .product-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 0.75rem;
        margin-bottom: 0.5rem;
        transition: all 0.3s ease;
    }
    
    .product-card:hover {
        border-color: var(--primary);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.15);
    }
    
    .product-name {
        font-weight: 600;
        font-size: 0.9rem;
        color: #2d3748;
    }
    
    .product-price {
        color: var(--primary);
        font-weight: 700;
    }
    
    .info-box {
        background: #f8f9fa;
        border-left: 4px solid var(--primary);
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    
    .success-box {
        background: #f0fff4;
        border-left: 4px solid var(--success);
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    
    .stats-box {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 12px;
        margin: 0.5rem 0;
        text-align: center;
    }
    
    .css-1d391kg, [data-testid="stSidebar"] {
        background-color: #f8f9fa !important;
    }
    
    .footer {
        text-align: center;
        padding: 1rem;
        color: #6c757d;
        font-size: 0.7rem;
        margin-top: 2rem;
        border-top: 1px solid #e2e8f0;
        background-color: #ffffff;
    }
    
    .stDataFrame, .stTable {
        background-color: #ffffff;
    }
    
    .stTabs [data-baseweb="tab-list"] button {
        background-color: #f8f9fa;
        color: #4a5568;
    }
    
    .stTextInput > div > div > input, 
    .stNumberInput > div > div > input,
    .stSelectbox > div > div,
    .stTextArea textarea {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
    }
    
    @media (max-width: 768px) {
        .metric-card {
            padding: 0.8rem;
        }
    }
</style>
""", unsafe_allow_html=True)

# ==================== INITIALISATION ====================
supabase = init_supabase()

# Vérifier si les données existent déjà en base
existing_clients = load_all_clients_from_supabase(supabase) if supabase else None
existing_orders = load_all_orders_from_supabase(supabase) if supabase else None

if existing_clients is not None and len(existing_clients) > 0:
    # Charger depuis Supabase
    st.session_state.df_clients = existing_clients
    st.session_state.historique_achats = existing_orders if existing_orders else []
    st.session_state.data_source = "Supabase"
    st.session_state.synced = True
else:
    # Générer les données locales
    np.random.seed(42)
    n = 100
    
    st.session_state.df_clients = pd.DataFrame({
        'client_id': range(1, n+1),
        'nom': [f"Client_{i}" for i in range(1, n+1)],
        'email': [f"client{i}@email.com" for i in range(1, n+1)],
        'âge': np.random.normal(35, 12, n).clip(18, 70).astype(int),
        'ville': np.random.choice(['Douala', 'Yaoundé', 'Garoua', 'Bafoussam', 'Bamenda'], n),
        'revenu_annuel_fcfa': np.random.normal(2_500_000, 800_000, n).clip(1_000_000, 8_000_000).astype(int),
        'ca_total_fcfa': np.random.exponential(500000, n).astype(int),
        'nb_achats': np.random.poisson(3, n)
    })
    st.session_state.historique_achats = []
    st.session_state.data_source = "Local"
    st.session_state.synced = False

# ==================== CATALOGUE PRODUITS ====================
PRODUITS = {
    'Smartphone Tecno': {'prix': 150000, 'categorie': 'Électronique', 'description': 'Téléphone dernière génération'},
    'Ordinateur Portable': {'prix': 450000, 'categorie': 'Électronique', 'description': 'PC haute performance'},
    'Écouteurs Bluetooth': {'prix': 25000, 'categorie': 'Électronique', 'description': 'Son haute qualité'},
    'Montre Connectée': {'prix': 75000, 'categorie': 'Électronique', 'description': 'Suivi santé'},
    'T-shirt Premium': {'prix': 8500, 'categorie': 'Mode', 'description': 'Coton bio'},
    'Jean Slim Fit': {'prix': 15000, 'categorie': 'Mode', 'description': 'Taille parfaite'},
    'Basket Sport': {'prix': 45000, 'categorie': 'Mode', 'description': 'Confortable'},
    'Veste Imperméable': {'prix': 35000, 'categorie': 'Mode', 'description': 'Anti-pluie'},
    'Canapé Moderne': {'prix': 250000, 'categorie': 'Maison', 'description': '3 places'},
    'Lampe LED': {'prix': 12000, 'categorie': 'Maison', 'description': 'Économique'},
    'Tapis Design': {'prix': 35000, 'categorie': 'Maison', 'description': 'Laine naturelle'},
    'Batterie Cuisine': {'prix': 55000, 'categorie': 'Maison', 'description': 'Anti-adhésive'},
    'Vélo Appartement': {'prix': 180000, 'categorie': 'Sports', 'description': 'Fitness'},
    'Ballon Match': {'prix': 8000, 'categorie': 'Sports', 'description': 'Taille 5'},
    'Sac Sport': {'prix': 20000, 'categorie': 'Sports', 'description': 'Grande capacité'},
    'Tapis Course': {'prix': 120000, 'categorie': 'Sports', 'description': 'Amorti renforcé'}
}

MODES_PAIEMENT = ['MTN Mobile Money', 'Orange Money', 'Carte Bancaire', 'Virement Bancaire']

def format_fcfa(x):
    if pd.isna(x) or x == 0:
        return "0 FCFA"
    return f"{x:,.0f} FCFA".replace(",", " ")

def enregistrer_achat(client_id, produits_achetes, montant_total, mode_paiement):
    achat = {
        'date': datetime.now(),
        'client_id': client_id,
        'produits': produits_achetes,
        'montant_fcfa': montant_total,
        'mode_paiement': mode_paiement,
        'nb_articles': len(produits_achetes)
    }
    st.session_state.historique_achats.append(achat)
    
    idx = st.session_state.df_clients[st.session_state.df_clients['client_id'] == client_id].index[0]
    st.session_state.df_clients.loc[idx, 'ca_total_fcfa'] += montant_total
    st.session_state.df_clients.loc[idx, 'nb_achats'] += 1
    
    # Sauvegarder dans Supabase si disponible
    if supabase:
        save_client_to_supabase(supabase, st.session_state.df_clients.loc[idx].to_dict())
        save_order_to_supabase(supabase, achat)
    
    return True

# ==================== HEADER ====================
data_source = st.session_state.get('data_source', 'Local')
st.markdown(f"""
<div class="main-header">
    <h1><i class="fas fa-store"></i> ShopAnalyzer Pro</h1>
    <p><i class="fas fa-chart-line"></i> Plateforme intelligente de collecte et d'analyse de données e-commerce</p>
    <p style="font-size: 0.85rem; margin-top: 0.5rem;">
        <i class="fas fa-database"></i> Source: <strong>{data_source}</strong> | 
        <i class="fas fa-users"></i> {len(st.session_state.df_clients)} clients | 
        <i class="fas fa-shopping-cart"></i> {len(st.session_state.historique_achats)} commandes
    </p>
</div>
""", unsafe_allow_html=True)

# Bouton de synchronisation manuelle
if supabase and not st.session_state.get('synced', False):
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔄 Synchroniser les 100 clients avec Supabase", use_container_width=True):
            with st.spinner("Synchronisation en cours..."):
                clients_saved, orders_saved = sync_all_to_supabase(
                    supabase, 
                    st.session_state.df_clients, 
                    st.session_state.historique_achats
                )
                st.session_state.synced = True
                st.success(f"✅ Synchronisation terminée ! {clients_saved} clients et {orders_saved} commandes sauvegardés dans Supabase.")
                time.sleep(2)
                st.rerun()

# ==================== SIDEBAR ====================
with st.sidebar:
    st.markdown("## 🎯 Navigation")
    
    menu = st.radio(
        "Menu",
        ["Nouvelle Commande", "Tableau de Bord", "Analyse Descriptive", "Analyses ML", "Clients", "Conseils"]
    )
    
    st.markdown("---")
    
    total_ventes = sum(a['montant_fcfa'] for a in st.session_state.historique_achats)
    nb_commandes = len(st.session_state.historique_achats)
    
    st.markdown(f"""
    <div style='background: #e9ecef; padding: 1rem; border-radius: 15px;'>
        <div style='display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.75rem;'>
            <i class='fas fa-money-bill-wave' style='font-size: 1.5rem; color: #667eea;'></i>
            <div>
                <div style='font-size: 0.7rem; color: #666;'>CA TOTAL</div>
                <div style='font-weight: bold;'>{format_fcfa(total_ventes)}</div>
            </div>
        </div>
        <div style='display: flex; align-items: center; gap: 0.5rem;'>
            <i class='fas fa-shopping-cart' style='font-size: 1.5rem; color: #667eea;'></i>
            <div>
                <div style='font-size: 0.7rem; color: #666;'>COMMANDES</div>
                <div style='font-weight: bold;'>{nb_commandes}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.caption("Développé par **Armelle** | Version Supabase")

# ==================== RESTE DU CODE (PAGES) ====================
# [Le reste de votre code pour les pages reste exactement identique]
# PAGE 1: FORMULAIRE
if menu == "Nouvelle Commande":
    st.markdown("## 🛒 Passer une commande")
    
    with st.form("formulaire_achat", clear_on_submit=True):
        col1, col2 = st.columns([1, 1], gap="large")
        
        with col1:
            st.markdown("### 👤 Vos informations")
            
            option_client = st.radio(
                "Type de client",
                ["Nouveau client", "Client existant"],
                horizontal=True
            )
            
            if option_client == "Client existant":
                client_id = st.selectbox(
                    "Sélectionnez votre compte",
                    st.session_state.df_clients['client_id'].tolist(),
                    format_func=lambda x: f"#{x} - {st.session_state.df_clients[st.session_state.df_clients['client_id']==x]['nom'].values[0]}"
                )
            else:
                col_a, col_b = st.columns(2)
                with col_a:
                    nom = st.text_input("Nom complet", placeholder="Votre nom")
                    age = st.number_input("Âge", 18, 100, 30)
                with col_b:
                    email = st.text_input("Email", placeholder="votre@email.com")
                    ville = st.selectbox("Ville", ['Douala', 'Yaoundé', 'Garoua', 'Bafoussam', 'Bamenda'])
        
        with col2:
            st.markdown("### 🛍️ Votre panier")
            
            produits_selectionnes = []
            montant_total = 0
            
            for categorie in ['Électronique', 'Mode', 'Maison', 'Sports']:
                with st.expander(f"📂 {categorie}"):
                    produits_cat = [(nom, info) for nom, info in PRODUITS.items() if info['categorie'] == categorie]
                    
                    for produit, info in produits_cat:
                        cols = st.columns([3, 1, 1])
                        with cols[0]:
                            st.markdown(f"""
                            <div class="product-card">
                                <span class="product-name">{produit}</span><br>
                                <span class="product-price">{format_fcfa(info['prix'])}</span>
                                <br><small>{info['description']}</small>
                            </div>
                            """, unsafe_allow_html=True)
                        with cols[1]:
                            quantite = st.number_input(
                                "Qté",
                                min_value=0, max_value=5,
                                key=produit,
                                label_visibility="collapsed"
                            )
                        with cols[2]:
                            if quantite > 0:
                                st.markdown(f'<span style="color: #48bb78;">✓ +{format_fcfa(info["prix"] * quantite)}</span>', 
                                          unsafe_allow_html=True)
                        
                        if quantite > 0:
                            produits_selectionnes.extend([produit] * quantite)
                            montant_total += info['prix'] * quantite
        
        st.markdown("---")
        st.markdown("### 💳 Paiement")
        
        mode_paiement = st.selectbox("Choisissez votre moyen de paiement", MODES_PAIEMENT)
        
        st.markdown(f"""
        <div class="success-box" style="text-align: center;">
            <i class="fas fa-receipt" style="font-size: 1.5rem;"></i>
            <div style="font-size: 0.9rem; margin-top: 0.5rem;">Total à payer</div>
            <div style="font-size: clamp(1.5rem, 5vw, 2rem); font-weight: 700; color: #667eea;">
                {format_fcfa(montant_total)}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        submitted = st.form_submit_button("✅ Confirmer la commande", use_container_width=True)
        
        if submitted:
            if montant_total == 0:
                st.error("❌ Veuillez sélectionner au moins un produit !")
            elif option_client == "Nouveau client" and ('nom' not in dir() or not nom):
                st.error("❌ Veuillez remplir vos informations")
            else:
                with st.spinner("⏳ Traitement de votre commande..."):
                    time.sleep(0.8)
                    
                    if option_client == "Nouveau client":
                        new_id = len(st.session_state.df_clients) + 1
                        nouveau_client = pd.DataFrame({
                            'client_id': [new_id],
                            'nom': [nom],
                            'email': [email],
                            'âge': [age],
                            'ville': [ville],
                            'revenu_annuel_fcfa': [0],
                            'ca_total_fcfa': [0],
                            'nb_achats': [0]
                        })
                        st.session_state.df_clients = pd.concat([st.session_state.df_clients, nouveau_client], ignore_index=True)
                        client_id = new_id
                    else:
                        client_id = client_id
                    
                    if enregistrer_achat(client_id, produits_selectionnes, montant_total, mode_paiement):
                        st.balloons()
                        st.success(f"🎉 Commande confirmée ! Merci pour votre achat de {format_fcfa(montant_total)}")

# PAGE 2: DASHBOARD
elif menu == "Tableau de Bord":
    st.markdown("## 📊 Tableau de bord")
    
    total_ventes = sum(a['montant_fcfa'] for a in st.session_state.historique_achats)
    nb_commandes = len(st.session_state.historique_achats)
    nb_clients_actifs = len(st.session_state.df_clients[st.session_state.df_clients['nb_achats'] > 0])
    panier_moyen = total_ventes / nb_commandes if nb_commandes > 0 else 0
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{format_fcfa(total_ventes)}</div>
            <div class="metric-label">Chiffre d'affaires</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{nb_commandes}</div>
            <div class="metric-label">Commandes</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{nb_clients_actifs}</div>
            <div class="metric-label">Clients actifs</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{format_fcfa(panier_moyen)}</div>
            <div class="metric-label">Panier moyen</div>
        </div>
        """, unsafe_allow_html=True)
    
    if st.session_state.historique_achats:
        col1, col2 = st.columns(2)
        
        with col1:
            df_ventes = pd.DataFrame(st.session_state.historique_achats)
            df_ventes['date'] = pd.to_datetime(df_ventes['date'])
            df_ventes['jour'] = df_ventes['date'].dt.date
            ventes_par_jour = df_ventes.groupby('jour')['montant_fcfa'].sum().reset_index()
            
            fig = px.bar(ventes_par_jour, x='jour', y='montant_fcfa',
                        title="📈 Évolution des ventes",
                        labels={'jour':'Date', 'montant_fcfa':'CA (FCFA)'})
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            tous_produits = []
            for achat in st.session_state.historique_achats:
                tous_produits.extend(achat['produits'])
            
            if tous_produits:
                top_produits = pd.Series(tous_produits).value_counts().head(6)
                fig = px.bar(x=top_produits.values, y=top_produits.index,
                            orientation='h', title="🏆 Top produits",
                            labels={'x':'Nombre de ventes', 'y':''})
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)

# PAGE 3: ANALYSE DESCRIPTIVE (version simplifiée pour garder la place)
elif menu == "Analyse Descriptive":
    st.markdown("## 📊 Analyse descriptive des données")
    st.markdown("*Statistiques détaillées et visualisations exploratoires*")
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 Clients", "🛍️ Ventes", "🏷️ Produits & Catégories", "⭐ Fidélité clients", "📈 Corrélations"])
    
    with tab1:
        st.markdown("### Analyse des clients")
        df_clients = st.session_state.df_clients
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("👥 Total clients", len(df_clients))
        with col2:
            st.metric("📅 Âge moyen", f"{df_clients['âge'].mean():.0f} ans")
        with col3:
            st.metric("💰 Revenu moyen", format_fcfa(df_clients['revenu_annuel_fcfa'].mean()))
        with col4:
            st.metric("💵 CA moyen/client", format_fcfa(df_clients['ca_total_fcfa'].mean()))
        
        fig_ages = px.histogram(df_clients, x='âge', nbins=30, title="Distribution des âges")
        st.plotly_chart(fig_ages, use_container_width=True)
        
        ville_counts = df_clients['ville'].value_counts()
        fig_ville = px.pie(values=ville_counts.values, names=ville_counts.index, title="Clients par ville")
        st.plotly_chart(fig_ville, use_container_width=True)
    
    with tab2:
        st.markdown("### Analyse des ventes")
        if st.session_state.historique_achats:
            df_ventes = pd.DataFrame(st.session_state.historique_achats)
            df_ventes['date'] = pd.to_datetime(df_ventes['date'])
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("💰 CA Total", format_fcfa(df_ventes['montant_fcfa'].sum()))
            with col2:
                st.metric("📦 Nb commandes", len(df_ventes))
            with col3:
                st.metric("🛒 Panier moyen", format_fcfa(df_ventes['montant_fcfa'].mean()))
            with col4:
                st.metric("📊 Articles/commande", f"{df_ventes['nb_articles'].mean():.1f}")
            
            ventes_jour = df_ventes.groupby(df_ventes['date'].dt.date)['montant_fcfa'].sum().reset_index()
            fig_evol = px.line(ventes_jour, x='date', y='montant_fcfa', title="Évolution du CA", markers=True)
            st.plotly_chart(fig_evol, use_container_width=True)
            
            paiements_counts = df_ventes['mode_paiement'].value_counts()
            fig_paiements = px.pie(values=paiements_counts.values, names=paiements_counts.index, title="Modes de paiement")
            st.plotly_chart(fig_paiements, use_container_width=True)
        else:
            st.info("Aucune vente enregistrée")
    
    with tab3:
        st.markdown("### Analyse des produits")
        if st.session_state.historique_achats:
            tous_produits = []
            for cmd in st.session_state.historique_achats:
                tous_produits.extend(cmd['produits'])
            
            if tous_produits:
                top_ventes = pd.Series(tous_produits).value_counts().head(10)
                fig_top = px.bar(x=top_ventes.values, y=top_ventes.index, orientation='h', title="Top 10 des produits")
                fig_top.update_layout(height=500)
                st.plotly_chart(fig_top, use_container_width=True)
    
    with tab4:
        st.markdown("### Fidélité clients")
        df_clients = st.session_state.df_clients
        clients_actifs = len(df_clients[df_clients['nb_achats'] > 0])
        clients_fideles = len(df_clients[df_clients['nb_achats'] >= 3])
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("👥 Clients actifs", clients_actifs)
        with col2:
            st.metric("⭐ Clients fidèles", clients_fideles)
        with col3:
            taux = (clients_fideles / clients_actifs * 100) if clients_actifs > 0 else 0
            st.metric("📈 Taux fidélisation", f"{taux:.1f}%")
        
        fig_achats = px.histogram(df_clients, x='nb_achats', nbins=15, title="Distribution des achats")
        st.plotly_chart(fig_achats, use_container_width=True)
    
    with tab5:
        st.markdown("### Corrélations")
        df_clients = st.session_state.df_clients
        cols_corr = ['âge', 'revenu_annuel_fcfa', 'ca_total_fcfa', 'nb_achats']
        corr_matrix = df_clients[cols_corr].corr()
        fig_corr = px.imshow(corr_matrix, text_auto=True, title="Matrice de corrélation", color_continuous_scale='RdBu')
        st.plotly_chart(fig_corr, use_container_width=True)

# PAGE 4: ANALYSES ML
elif menu == "Analyses ML":
    st.markdown("## 📈 Analyses prédictives")
    
    df_ml = st.session_state.df_clients[st.session_state.df_clients['nb_achats'] > 0]
    
    if len(df_ml) > 5:
        tab1, tab2, tab3 = st.tabs(["📊 Régression", "🎯 Clustering", "🔮 Prédiction"])
        
        with tab1:
            X = df_ml[['âge', 'revenu_annuel_fcfa']]
            y = df_ml['ca_total_fcfa']
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            reg_multiple = LinearRegression()
            reg_multiple.fit(X_train, y_train)
            score_multiple = reg_multiple.score(X_test, y_test)
            
            st.metric("R² Score", f"{max(0, score_multiple):.2%}")
            
            y_pred = reg_multiple.predict(X_test)
            fig_compare = go.Figure()
            fig_compare.add_trace(go.Scatter(x=y_test, y=y_pred, mode='markers', name='Prédictions'))
            fig_compare.add_trace(go.Scatter(x=[y.min(), y.max()], y=[y.min(), y.max()], mode='lines', name='Idéal', line=dict(dash='dash', color='red')))
            st.plotly_chart(fig_compare, use_container_width=True)
        
        with tab2:
            features = df_ml[['âge', 'ca_total_fcfa']]
            scaler = StandardScaler()
            features_scaled = scaler.fit_transform(features)
            kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
            df_ml['segment'] = kmeans.fit_predict(features_scaled)
            
            fig_clust = px.scatter(df_ml, x='ca_total_fcfa', y='âge', color='segment', size='nb_achats', title="Segmentation clients")
            st.plotly_chart(fig_clust, use_container_width=True)
        
        with tab3:
            age_pred = st.slider("Âge", 18, 70, 35)
            revenu_pred = st.number_input("Revenu annuel (FCFA)", 500000, 8000000, 2500000)
            if st.button("Prédire"):
                pred = reg_multiple.predict([[age_pred, revenu_pred]])[0]
                st.success(f"💰 CA estimé: {format_fcfa(pred)}")
    else:
        st.info("Besoin d'au moins 5 clients actifs")

# PAGE 5: CLIENTS
elif menu == "Clients":
    st.markdown("## 👥 Gestion des clients")
    
    df_display = st.session_state.df_clients.copy()
    df_display['ca_total_fcfa'] = df_display['ca_total_fcfa'].apply(format_fcfa)
    df_display['revenu_annuel_fcfa'] = df_display['revenu_annuel_fcfa'].apply(format_fcfa)
    st.dataframe(df_display, use_container_width=True)
    
    if st.session_state.historique_achats:
        st.markdown("### 📜 Historique des commandes")
        df_histo = pd.DataFrame(st.session_state.historique_achats)
        df_histo['date'] = df_histo['date'].dt.strftime('%d/%m/%Y %H:%M')
        df_histo['montant_fcfa'] = df_histo['montant_fcfa'].apply(format_fcfa)
        st.dataframe(df_histo, use_container_width=True)

# PAGE 6: CONSEILS
else:
    st.markdown("## 💡 Conseils et bonnes pratiques")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class="info-box">
            <h3><i class="fas fa-mobile-alt"></i> Pour une meilleure expérience</h3>
            <ul>
                <li><i class="fas fa-globe"></i> Utilisez Chrome, Firefox ou Safari</li>
                <li><i class="fas fa-tablet-alt"></i> Le site est adapté aux mobiles</li>
                <li><i class="fas fa-lock"></i> Vos données sont sécurisées</li>
                <li><i class="fas fa-credit-card"></i> Paiements sécurisés</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="info-box">
            <h3><i class="fas fa-star"></i> Fonctionnalités clés</h3>
            <ul>
                <li><i class="fas fa-chart-pie"></i> Dashboard interactif</li>
                <li><i class="fas fa-chart-bar"></i> Analyse descriptive complète</li>
                <li><i class="fas fa-robot"></i> Prédiction du CA par IA</li>
                <li><i class="fas fa-chart-line"></i> Segmentation clients</li>
                <li><i class="fas fa-database"></i> Données persistantes Supabase</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

# ==================== FOOTER ====================
st.markdown(f"""
<div class="footer">
    <hr>
    <p>
        <i class="fas fa-store"></i> ShopAnalyzer by Armelle | 
        <i class="fas fa-chart-bar"></i> Analyse descriptive complète |
        <i class="fas fa-database"></i> Données synchronisées avec Supabase
    </p>
    <p>
        <i class="fas fa-money-bill-wave"></i> Toutes les valeurs en FCFA | 
        <i class="fas fa-calendar-alt"></i> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
    </p>
</div>
""", unsafe_allow_html=True)
