# app_supabase_final.py - Version avec Supabase intégré
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression
from sklearn.cluster import KMeans
from sklearn.metrics import r2_score, silhouette_score
from supabase import create_client, Client
import time
import warnings
import hashlib
warnings.filterwarnings('ignore')

# ==================== CONFIGURATION SUPABASE ====================
# ⚠️ REMPLACEZ PAR VOS IDENTIFIANTS SUPABASE ⚠️
SUPABASE_URL = "https://lojxytucxpxvxvqdelue.supabase.co"  # Ex: https://abcdefghijk.supabase.co
SUPABASE_ANON_KEY = "sb_publishable_dABCJ88o2IvCZTrPHpuR3g_A0zl6Q57"  # Ex: eyJhbGciOiJIUzI1NiIs...

@st.cache_resource
def init_supabase() -> Client:
    """Initialise la connexion Supabase"""
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

def hash_password(password: str) -> str:
    """Hache le mot de passe"""
    return hashlib.sha256(password.encode()).hexdigest()

# ==================== FONCTIONS SUPABASE ====================
def register_user(supabase, username, password, email, ville, age):
    """Enregistre un nouvel utilisateur dans la table users"""
    try:
        data = {
            'username': username,
            'password': hash_password(password),
            'email': email,
            'ville': ville,
            'age': age,
            'created_at': datetime.now().isoformat(),
            'last_login': None,
            'total_depenses': 0,
            'nb_commandes': 0
        }
        result = supabase.table('users').insert(data).execute()
        return True, "✅ Compte créé avec succès !"
    except Exception as e:
        if 'duplicate' in str(e).lower():
            return False, "❌ Ce nom d'utilisateur existe déjà !"
        return False, f"❌ Erreur: {str(e)[:100]}"

def login_user(supabase, username, password):
    """Connecte un utilisateur"""
    try:
        hashed = hash_password(password)
        result = supabase.table('users').select('*').eq('username', username).eq('password', hashed).execute()
        if result.data:
            # Mettre à jour last_login
            supabase.table('users').update({'last_login': datetime.now().isoformat()}).eq('username', username).execute()
            return True, result.data[0]
        return False, None
    except Exception as e:
        return False, None

def get_user_data(supabase, username):
    """Récupère les données d'un utilisateur"""
    try:
        result = supabase.table('users').select('*').eq('username', username).execute()
        return result.data[0] if result.data else None
    except:
        return None

def save_order_to_supabase(supabase, username, order_data):
    """Enregistre une commande dans la table commandes"""
    try:
        data = {
            'username': username,
            'date': datetime.now().isoformat(),
            'montant_fcfa': order_data['montant_total'],
            'nb_articles': order_data['nb_articles'],
            'produits': ','.join(order_data['produits']),
            'mode_paiement': order_data['mode_paiement'],
            'categorie_principale': order_data.get('categorie_principale', '')
        }
        result = supabase.table('commandes').insert(data).execute()
        
        # Mettre à jour les stats utilisateur
        user = get_user_data(supabase, username)
        if user:
            supabase.table('users').update({
                'total_depenses': user.get('total_depenses', 0) + order_data['montant_total'],
                'nb_commandes': user.get('nb_commandes', 0) + 1
            }).eq('username', username).execute()
        return True
    except Exception as e:
        st.error(f"Erreur sauvegarde: {e}")
        return False

def get_user_orders(supabase, username):
    """Récupère les commandes d'un utilisateur"""
    try:
        result = supabase.table('commandes').select('*').eq('username', username).order('date', desc=True).execute()
        return result.data if result.data else []
    except:
        return []

def get_all_orders(supabase):
    """Récupère toutes les commandes (admin)"""
    try:
        result = supabase.table('commandes').select('*').order('date', desc=True).execute()
        return result.data if result.data else []
    except:
        return []

def get_all_users(supabase):
    """Récupère tous les utilisateurs"""
    try:
        result = supabase.table('users').select('*').order('created_at', desc=True).execute()
        return result.data if result.data else []
    except:
        return []

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
    
    .login-container {
        max-width: 450px;
        margin: 50px auto;
        padding: 30px;
        background: white;
        border-radius: 20px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.1);
    }
    
    @media (max-width: 768px) {
        .metric-card {
            padding: 0.8rem;
        }
    }
</style>
""", unsafe_allow_html=True)

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

# ==================== PAGE DE CONNEXION ====================
def show_login():
    """Affiche la page de connexion"""
    supabase = init_supabase()
    
    st.markdown("""
    <div class="login-container">
        <div style="text-align:center">
            <h1 style="color:#667eea">🛍️ ShopAnalyzer Pro</h1>
            <p>Connectez-vous pour accéder à votre espace</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.5, 1])
    
    with col2:
        tab1, tab2 = st.tabs(["🔐 CONNEXION", "📝 INSCRIPTION"])
        
        with tab1:
            username = st.text_input("Nom d'utilisateur", key="login_user")
            password = st.text_input("Mot de passe", type="password", key="login_pwd")
            
            if st.button("Se connecter", use_container_width=True):
                if username and password:
                    success, user_data = login_user(supabase, username, password)
                    if success:
                        st.session_state.authenticated = True
                        st.session_state.username = username
                        st.session_state.user_data = user_data
                        st.session_state.supabase = supabase
                        st.rerun()
                    else:
                        st.error("❌ Identifiants incorrects !")
                else:
                    st.warning("Veuillez remplir tous les champs")
        
        with tab2:
            new_user = st.text_input("Nom d'utilisateur", key="reg_user")
            new_pwd = st.text_input("Mot de passe", type="password", key="reg_pwd")
            confirm_pwd = st.text_input("Confirmer le mot de passe", type="password")
            email = st.text_input("Email", key="reg_email")
            ville = st.selectbox("Ville", ['Douala', 'Yaoundé', 'Garoua', 'Bafoussam', 'Bamenda'])
            age = st.number_input("Âge", 18, 100, 30)
            
            if st.button("Créer mon compte", use_container_width=True):
                if new_user and new_pwd and email:
                    if new_pwd != confirm_pwd:
                        st.error("❌ Les mots de passe ne correspondent pas !")
                    elif len(new_pwd) < 4:
                        st.error("❌ Mot de passe trop court (min 4 caractères)")
                    else:
                        success, msg = register_user(supabase, new_user, new_pwd, email, ville, age)
                        if success:
                            st.success(msg)
                            st.balloons()
                            st.info("Vous pouvez maintenant vous connecter")
                        else:
                            st.error(msg)
                else:
                    st.warning("Veuillez remplir tous les champs obligatoires")

# ==================== HEADER ====================
def show_header():
    supabase = st.session_state.get('supabase')
    username = st.session_state.get('username')
    
    st.markdown(f"""
    <div class="main-header">
        <h1><i class="fas fa-store"></i> ShopAnalyzer Pro</h1>
        <p><i class="fas fa-chart-line"></i> Plateforme intelligente de collecte et d'analyse de données e-commerce</p>
        <p style="font-size: 0.85rem; margin-top: 0.5rem;">
            <i class="fas fa-mobile-alt"></i> Interface responsive | 
            <i class="fab fa-font-awesome"></i> Icônes Font Awesome | 
            <i class="fas fa-chart-bar"></i> Analyse descriptive incluse
        </p>
        <p style="font-size: 0.8rem; margin-top: 0.5rem;">👋 Bienvenue <strong>{username}</strong> !</p>
    </div>
    """, unsafe_allow_html=True)

# ==================== SIDEBAR ====================
def show_sidebar():
    supabase = st.session_state.get('supabase')
    user_data = st.session_state.get('user_data', {})
    
    with st.sidebar:
        st.markdown("## 🎯 Navigation")
        
        menu = st.radio(
            "Menu",
            ["Nouvelle Commande", "Tableau de Bord", "Analyse Descriptive", "Analyses ML", "Clients", "Conseils", "📜 Mon Historique"]
        )
        
        st.markdown("---")
        
        # Infos utilisateur
        st.markdown(f"""
        <div style='background: #e9ecef; padding: 1rem; border-radius: 15px;'>
            <div style='display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.75rem;'>
                <i class='fas fa-user' style='font-size: 1.2rem; color: #667eea;'></i>
                <div>
                    <div style='font-size: 0.7rem; color: #666;'>UTILISATEUR</div>
                    <div style='font-weight: bold;'>{st.session_state.get('username', '')}</div>
                </div>
            </div>
            <div style='display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.75rem;'>
                <i class='fas fa-shopping-cart' style='font-size: 1.2rem; color: #667eea;'></i>
                <div>
                    <div style='font-size: 0.7rem; color: #666;'>COMMANDES</div>
                    <div style='font-weight: bold;'>{user_data.get('nb_commandes', 0)}</div>
                </div>
            </div>
            <div style='display: flex; align-items: center; gap: 0.5rem;'>
                <i class='fas fa-money-bill-wave' style='font-size: 1.2rem; color: #667eea;'></i>
                <div>
                    <div style='font-size: 0.7rem; color: #666;'>DÉPENSES</div>
                    <div style='font-weight: bold;'>{format_fcfa(user_data.get('total_depenses', 0))}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        if st.button("🚪 Se déconnecter", use_container_width=True):
            for key in ['authenticated', 'username', 'user_data', 'supabase']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
        
        st.markdown("---")
        st.caption("Développé par **Armelle** | Version 5.0")
    
    return menu

# ==================== PAGE NOUVELLE COMMANDE ====================
def page_nouvelle_commande():
    supabase = st.session_state.get('supabase')
    username = st.session_state.get('username')
    user_data = st.session_state.get('user_data', {})
    
    st.markdown("## 🛒 Passer une commande")
    
    with st.form("formulaire_achat", clear_on_submit=True):
        col1, col2 = st.columns([1, 1], gap="large")
        
        with col1:
            st.markdown("### 👤 Vos informations")
            nom = st.text_input("Nom complet", value=user_data.get('email', '').split('@')[0] if user_data else "")
            email = st.text_input("Email", value=user_data.get('email', '') if user_data else "")
            age = st.number_input("Âge", 18, 100, value=user_data.get('age', 30) if user_data else 30)
            ville = st.selectbox("Ville", ['Douala', 'Yaoundé', 'Garoua', 'Bafoussam', 'Bamenda'],
                                index=0 if not user_data else (['Douala', 'Yaoundé', 'Garoua', 'Bafoussam', 'Bamenda'].index(user_data.get('ville', 'Douala')) if user_data.get('ville') in ['Douala', 'Yaoundé', 'Garoua', 'Bafoussam', 'Bamenda'] else 0))
        
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
                                key=f"{categorie}_{produit}",
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
            else:
                with st.spinner("⏳ Traitement de votre commande..."):
                    time.sleep(0.8)
                    
                    order_data = {
                        'montant_total': montant_total,
                        'nb_articles': len(produits_selectionnes),
                        'produits': produits_selectionnes,
                        'mode_paiement': mode_paiement,
                        'categorie_principale': 'General'
                    }
                    
                    if save_order_to_supabase(supabase, username, order_data):
                        st.balloons()
                        st.success(f"🎉 Commande confirmée ! Merci pour votre achat de {format_fcfa(montant_total)}")
                        
                        # Recharger les données utilisateur
                        new_data = get_user_data(supabase, username)
                        if new_data:
                            st.session_state.user_data = new_data
                        st.rerun()
                    else:
                        st.error("❌ Erreur lors de l'enregistrement")

# ==================== PAGE TABLEAU DE BORD ====================
def page_tableau_bord():
    supabase = st.session_state.get('supabase')
    
    st.markdown("## 📊 Tableau de bord")
    
    all_orders = get_all_orders(supabase)
    all_users = get_all_users(supabase)
    
    total_ventes = sum(o.get('montant_fcfa', 0) for o in all_orders)
    nb_commandes = len(all_orders)
    nb_clients = len(all_users)
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
            <div class="metric-value">{nb_clients}</div>
            <div class="metric-label">Clients</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{format_fcfa(panier_moyen)}</div>
            <div class="metric-label">Panier moyen</div>
        </div>
        """, unsafe_allow_html=True)
    
    if all_orders:
        col1, col2 = st.columns(2)
        
        with col1:
            df_ventes = pd.DataFrame(all_orders)
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
            for order in all_orders:
                if order.get('produits'):
                    produits = order['produits'].split(',')
                    tous_produits.extend(produits)
            
            if tous_produits:
                top_produits = pd.Series(tous_produits).value_counts().head(6)
                fig = px.bar(x=top_produits.values, y=top_produits.index,
                            orientation='h', title="🏆 Top produits",
                            labels={'x':'Nombre de ventes', 'y':''})
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)

# ==================== PAGE ANALYSE DESCRIPTIVE ====================
def page_analyse_descriptive():
    supabase = st.session_state.get('supabase')
    
    st.markdown("## 📊 Analyse descriptive des données")
    st.markdown("*Statistiques détaillées et visualisations exploratoires*")
    
    all_orders = get_all_orders(supabase)
    all_users = get_all_users(supabase)
    
    if not all_orders:
        st.info("📊 Aucune donnée disponible pour l'instant. Effectuez des commandes !")
        return
    
    df_ventes = pd.DataFrame(all_orders)
    df_ventes['date'] = pd.to_datetime(df_ventes['date'])
    df_clients = pd.DataFrame(all_users) if all_users else pd.DataFrame()
    
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Clients", "🛍️ Ventes", "🏷️ Produits & Catégories", "⭐ Fidélité clients"])
    
    with tab1:
        st.markdown("### Analyse des clients")
        
        if not df_clients.empty:
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("👥 Total clients", len(df_clients))
            with col2:
                age_moyen = df_clients['age'].mean() if 'age' in df_clients else 0
                st.metric("📅 Âge moyen", f"{age_moyen:.0f} ans")
            with col3:
                st.metric("📦 Clients actifs", len(df_clients[df_clients['nb_commandes'] > 0]))
            with col4:
                ca_moyen = df_clients['total_depenses'].mean()
                st.metric("💰 CA moyen/client", format_fcfa(ca_moyen))
            
            # Distribution par ville
            if 'ville' in df_clients:
                ville_counts = df_clients['ville'].value_counts()
                fig_ville = px.pie(values=ville_counts.values, names=ville_counts.index,
                                  title="Clients par ville")
                st.plotly_chart(fig_ville, use_container_width=True)
    
    with tab2:
        st.markdown("### Analyse des ventes")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("💰 CA Total", format_fcfa(df_ventes['montant_fcfa'].sum()))
        with col2:
            st.metric("📦 Nombre ventes", len(df_ventes))
        with col3:
            st.metric("🛒 Panier moyen", format_fcfa(df_ventes['montant_fcfa'].mean()))
        with col4:
            st.metric("📊 Articles/commande", f"{df_ventes['nb_articles'].mean():.1f}")
        
        # Évolution
        ventes_jour = df_ventes.groupby(df_ventes['date'].dt.date)['montant_fcfa'].sum().reset_index()
        fig_evol = px.line(ventes_jour, x='date', y='montant_fcfa',
                          title="Évolution du chiffre d'affaires",
                          markers=True)
        st.plotly_chart(fig_evol, use_container_width=True)
        
        # Distribution
        col1, col2 = st.columns(2)
        with col1:
            fig_montants = px.histogram(df_ventes, x='montant_fcfa', nbins=30,
                                       title="Distribution des montants")
            st.plotly_chart(fig_montants, use_container_width=True)
        with col2:
            fig_articles = px.histogram(df_ventes, x='nb_articles', nbins=10,
                                       title="Distribution des articles")
            st.plotly_chart(fig_articles, use_container_width=True)
        
        # Modes de paiement
        paiements_counts = df_ventes['mode_paiement'].value_counts()
        fig_paiements = px.pie(values=paiements_counts.values, names=paiements_counts.index,
                              title="Modes de paiement")
        st.plotly_chart(fig_paiements, use_container_width=True)
    
    with tab3:
        st.markdown("### Analyse des produits et catégories")
        
        tous_produits = []
        for order in all_orders:
            if order.get('produits'):
                prods = order['produits'].split(',')
                tous_produits.extend(prods)
        
        if tous_produits:
            top_ventes = pd.Series(tous_produits).value_counts().head(10)
            fig_top = px.bar(x=top_ventes.values, y=top_ventes.index, orientation='h',
                            title="Top 10 des produits les plus vendus")
            fig_top.update_layout(height=500)
            st.plotly_chart(fig_top, use_container_width=True)
            
            # Catégories
            categories_counts = df_ventes['categorie_principale'].value_counts()
            if len(categories_counts) > 0:
                fig_cat = px.pie(values=categories_counts.values, names=categories_counts.index,
                                title="Ventes par catégorie")
                st.plotly_chart(fig_cat, use_container_width=True)
    
    with tab4:
        st.markdown("### Analyse de la fidélité clients")
        
        if not df_clients.empty:
            col1, col2, col3 = st.columns(3)
            clients_actifs = len(df_clients[df_clients['nb_commandes'] > 0])
            clients_fideles = len(df_clients[df_clients['nb_commandes'] >= 3])
            
            with col1:
                st.metric("👥 Clients actifs", clients_actifs)
            with col2:
                st.metric("⭐ Clients fidèles", clients_fideles)
            with col3:
                taux = (clients_fideles / clients_actifs * 100) if clients_actifs > 0 else 0
                st.metric("📈 Taux de fidélisation", f"{taux:.1f}%")
            
            # Distribution
            fig_achats = px.histogram(df_clients, x='nb_commandes', nbins=15,
                                     title="Distribution du nombre d'achats par client")
            st.plotly_chart(fig_achats, use_container_width=True)
            
            # Top clients
            top_fideles = df_clients.nlargest(10, 'nb_commandes')[['username', 'nb_commandes', 'total_depenses']]
            top_fideles['total_depenses'] = top_fideles['total_depenses'].apply(format_fcfa)
            st.dataframe(top_fideles, use_container_width=True)

# ==================== PAGE ANALYSES ML ====================
def page_analyses_ml():
    st.markdown("## 📈 Analyses prédictives")
    st.info("📊 Module d'analyse prédictive - Disponible avec plus de données")
    
    # Simulation simple
    st.markdown("### 🔮 Simulateur de panier")
    col1, col2 = st.columns(2)
    with col1:
        nb_produits = st.slider("Nombre de produits", 1, 10, 3)
    with col2:
        prix_moyen = st.number_input("Prix moyen (FCFA)", 5000, 500000, 40000)
    
    estimation = nb_produits * prix_moyen
    st.success(f"💰 Estimation du panier : **{format_fcfa(estimation)}**")

# ==================== PAGE CLIENTS ====================
def page_clients():
    supabase = st.session_state.get('supabase')
    
    st.markdown("## 👥 Gestion des clients")
    
    all_users = get_all_users(supabase)
    
    if all_users:
        df_users = pd.DataFrame(all_users)
        df_display = df_users[['username', 'email', 'ville', 'age', 'nb_commandes', 'total_depenses']].copy()
        df_display['total_depenses'] = df_display['total_depenses'].apply(format_fcfa)
        st.dataframe(df_display, use_container_width=True)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("👥 Total clients", len(df_users))
        with col2:
            st.metric("⭐ Clients actifs", len(df_users[df_users['nb_commandes'] > 0]))
        with col3:
            ca_moyen = df_users['total_depenses'].mean()
            st.metric("💰 CA moyen/client", format_fcfa(ca_moyen))
    else:
        st.info("Aucun client enregistré")

# ==================== PAGE CONSEILS ====================
def page_conseils():
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
                <li><i class="fas fa-database"></i> Données persistantes (Supabase)</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

# ==================== PAGE MON HISTORIQUE ====================
def page_mon_historique():
    supabase = st.session_state.get('supabase')
    username = st.session_state.get('username')
    user_data = st.session_state.get('user_data', {})
    
    st.markdown("## 📜 Mon historique de commandes")
    
    orders = get_user_orders(supabase, username)
    
    if orders:
        df_orders = pd.DataFrame(orders)
        df_orders['montant_fcfa'] = df_orders['montant_fcfa'].apply(format_fcfa)
        df_orders['date'] = pd.to_datetime(df_orders['date']).dt.strftime('%d/%m/%Y à %H:%M')
        st.dataframe(df_orders[['date', 'montant_fcfa', 'nb_articles', 'mode_paiement']], use_container_width=True)
        
        st.markdown("### 📊 Mes statistiques")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("💰 Total dépensé", format_fcfa(user_data.get('total_depenses', 0)))
        with col2:
            st.metric("📦 Nombre de commandes", user_data.get('nb_commandes', 0))
        with col3:
            panier_moyen = user_data.get('total_depenses', 0) / max(1, user_data.get('nb_commandes', 0))
            st.metric("🛒 Panier moyen", format_fcfa(panier_moyen))
        
        # Badge de fidélité
        nb_cmd = user_data.get('nb_commandes', 0)
        if nb_cmd >= 10:
            st.success("🏆 **AMBASSADEUR** - Client exceptionnel !")
        elif nb_cmd >= 5:
            st.success("⭐ **FIDÈLE** - Merci pour votre confiance !")
        elif nb_cmd >= 2:
            st.info("🌟 **CLIENT RÉGULIER** - Continuez comme ça !")
        else:
            st.info("🆕 **NOUVEAU CLIENT** - Faites plus d'achats pour débloquer des avantages !")
    else:
        st.info("📭 Aucune commande pour le moment. Effectuez votre premier achat !")

# ==================== MAIN ====================
def main():
    # Initialiser l'état de session
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    
    # Si non authentifié, afficher la page de connexion
    if not st.session_state.authenticated:
        show_login()
    else:
        # Afficher l'application principale
        show_header()
        menu = show_sidebar()
        
        if menu == "Nouvelle Commande":
            page_nouvelle_commande()
        elif menu == "Tableau de Bord":
            page_tableau_bord()
        elif menu == "Analyse Descriptive":
            page_analyse_descriptive()
        elif menu == "Analyses ML":
            page_analyses_ml()
        elif menu == "Clients":
            page_clients()
        elif menu == "Conseils":
            page_conseils()
        elif menu == "📜 Mon Historique":
            page_mon_historique()
    
    # Footer
    st.markdown(f"""
    <div class="footer">
        <hr>
        <p>
            <i class="fas fa-store"></i> ShopAnalyzer by Armelle | 
            <i class="fas fa-chart-bar"></i> Analyse descriptive complète |
            <i class="fas fa-database"></i> Données persistantes Supabase
        </p>
        <p>
            <i class="fas fa-money-bill-wave"></i> Toutes les valeurs en FCFA | 
            <i class="fas fa-calendar-alt"></i> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
        </p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main() 
               
