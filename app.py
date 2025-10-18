from flask import Flask, request, redirect, url_for, session, jsonify, render_template_string
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, auth, firestore
from functools import wraps
import time
from datetime import datetime, timedelta

# ----------------- KONFIGIRASYON FIREBASE -----------------
SERVICE_ACCOUNT_FILE = "quiz-foot-service-account.json"

try:
    cred = credentials.Certificate(SERVICE_ACCOUNT_FILE)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("=" * 60)
    print("✅ SIKSÈ: Koneksyon Firebase reyisi!")
    print("=" * 60)
except FileNotFoundError:
    print("=" * 60)
    print(f"❌ ERÈ: Fichye '{SERVICE_ACCOUNT_FILE}' pa jwenn!")
    print("=" * 60)
    exit()
except Exception as e:
    print("=" * 60)
    print(f"❌ ERÈ FIREBASE: {str(e)}")
    print("=" * 60)
    exit()

# ----------------- KONFIGIRASYON FLASK -----------------
app = Flask(__name__)
CORS(app, supports_credentials=True, resources={r"/*": {"origins": "*"}})
app.secret_key = 'Yon_Kle_Sekre_Tres_Long_E_Konplike_Pou_Quiz_Foot_2024_Sekirize'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

# ----------------- BAZ DONE MATCH -----------------
MATCH_DATABASE = {
    "101": {"name": "REAL MADRID vs FC BARCELONA", "league": "Liga Chanpyon", "date": "25 Oktòb 2025 @ 2:00 PM", "ppv_price": 4.99, "is_ppv": True},
    "102": {"name": "MANCHESTER CITY vs LIVERPOOL FC", "league": "Premier League", "date": "26 Oktòb 2025 @ 10:30 AM", "ppv_price": 0.00, "is_ppv": False},
    "103": {"name": "JUVENTUS vs INTER MILAN", "league": "Serie A", "date": "26 Oktòb 2025 @ 4:45 PM", "ppv_price": 2.99, "is_ppv": True},
    "104": {"name": "PSG vs MARSEILLE", "league": "Ligue 1", "date": "27 Oktòb 2025 @ 1:00 PM", "ppv_price": 0.00, "is_ppv": False}
}

# ----------------- HTML TEMPLATES (MODIFIE) -----------------

BASE_HTML = """<!DOCTYPE html>
<html lang="ht">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }} - Quiz Foot</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%); min-height: 100vh; }
        .hero { background: linear-gradient(rgba(15, 12, 41, 0.8), rgba(15, 12, 41, 0.9)); }
        /* Style pou Spinner */
        .spinner {
            border: 4px solid rgba(255, 255, 255, 0.3);
            border-top: 4px solid #fff;
            border-radius: 50%;
            width: 20px;
            height: 20px;
            animation: spin 1s linear infinite;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
    {% block head_extra %}{% endblock %}
</head>
<body class="text-gray-100 {% if is_centered %}flex items-center justify-center min-h-screen{% endif %}">
    {% if not is_centered %}
    <header class="bg-gray-800 shadow-lg px-6 py-4 flex justify-between items-center">
        <div class="text-2xl font-bold text-orange-500">⚽ QUIZ FOOT</div>
        <nav class="flex gap-4">
            <a href="/" class="text-gray-200 hover:text-white">Akèy</a>
            {% if logged_in %}
                <a href="/dashboard" class="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-lg">Dashboard</a>
                <a href="/logout" class="bg-red-600 hover:bg-red-700 px-4 py-2 rounded-lg">Dekonekte</a>
            {% else %}
                <a href="/login" class="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-lg">Konekte</a>
                <a href="/signup" class="bg-green-600 hover:bg-green-700 px-4 py-2 rounded-lg">Enskri</a>
            {% endif %}
        </nav>
    </header>
    {% endif %}

    <main {% if not is_centered %}class="container mx-auto px-4 py-8"{% endif %}>
        {% block content %}{% endblock %}
    </main>
    
    {% if not is_centered %}
    <footer class="bg-gray-800 text-center py-6 mt-12">
        <p class="text-gray-400">&copy; 2025 Quiz Foot. Tout Dwa Rezève.</p>
    </footer>
    {% endif %}
</body>
</html>"""

INDEX_HTML = BASE_HTML.replace('{% block content %}{% endblock %}', """
{% block content %}
<main class="container mx-auto px-4 py-20">
    <section class="hero text-center py-24 rounded-xl mb-12">
        <h1 class="text-5xl font-bold mb-6 text-white">🏆 Gade Tout Match Foutbòl yo an Dirèk!</h1>
        <p class="text-xl mb-8 text-gray-300">Aksè san limit pou sèlman $9.99 pa mwa</p>
        {% if logged_in %}
            <a href="/dashboard" class="bg-orange-500 hover:bg-orange-600 text-white px-8 py-4 rounded-full text-lg font-bold">Ale sou Dashboard</a>
        {% else %}
            <a href="/signup" class="bg-orange-500 hover:bg-orange-600 text-white px-8 py-4 rounded-full text-lg font-bold">Kòmanse Kounye a</a>
        {% endif %}
    </section>
    
    <section>
        <h2 class="text-3xl font-bold text-center mb-8">⚡ Match Disponib</h2>
        <div class="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            <div class="bg-gray-800 p-6 rounded-xl">
                <h3 class="text-blue-400 font-bold mb-2">Champions League</h3>
                <p class="text-xl font-bold mb-2">REAL MADRID vs FC BARCELONA</p>
                <p class="text-gray-400 text-sm mb-4">📅 25 Oktòb 2025 @ 2:00 PM</p>
                <span class="bg-red-600 text-white px-3 py-1 rounded text-sm">💰 PPV $4.99</span>
            </div>
            <div class="bg-gray-800 p-6 rounded-xl">
                <h3 class="text-blue-400 font-bold mb-2">Premier League</h3>
                <p class="text-xl font-bold mb-2">MANCHESTER CITY vs LIVERPOOL</p>
                <p class="text-gray-400 text-sm mb-4">📅 26 Oktòb 2025 @ 10:30 AM</p>
                <span class="bg-green-600 text-white px-3 py-1 rounded text-sm">🆓 GRATIS</span>
            </div>
        </div>
    </section>
</main>
{% endblock %}
""")

LOGIN_HTML = BASE_HTML.replace('<body class="text-gray-100', '<body class="text-gray-100').replace('{% block content %}{% endblock %}', """
{% block head_extra %}
<style>
    body { background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); }
</style>
{% endblock %}
{% block content %}
<div class="bg-gray-800 p-8 rounded-xl shadow-2xl max-w-md w-full">
    <h2 class="text-3xl font-bold text-white text-center mb-6">🔐 Konekte</h2>
    <div id="error-message" class="hidden bg-red-900 text-red-200 p-3 rounded mb-4"></div>
    <form id="login-form">
        <input type="email" id="email" placeholder="Email" required 
            class="w-full p-3 mb-4 bg-gray-700 text-white rounded border-2 border-gray-600 focus:border-blue-500">
        <input type="password" id="password" placeholder="Modpas" required 
            class="w-full p-3 mb-4 bg-gray-700 text-white rounded border-2 border-gray-600 focus:border-blue-500">
        <button type="submit" id="login-btn" class="w-full bg-orange-500 hover:bg-orange-600 text-white py-3 rounded font-bold flex items-center justify-center relative">
            <span id="btn-text">Konekte</span>
            <div id="spinner" class="spinner absolute right-4 hidden"></div>
        </button>
    </form>
    <p class="text-center mt-4 text-gray-300">
        Pa gen kont? <a href="/signup" class="text-blue-400 hover:underline">Enskri</a>
    </p>
    <p class="text-center mt-2">
        <a href="/forgot_password" class="text-red-400 hover:underline">Bliye Modpas?</a>
    </p>
    <p class="text-center mt-2">
        <a href="/" class="text-gray-400 hover:text-white">← Retounen Akèy</a>
    </p>
</div>

<script type="module">
    import { initializeApp } from 'https://www.gstatic.com/firebasejs/11.6.1/firebase-app.js';
    import { getAuth, signInWithEmailAndPassword } from 'https://www.gstatic.com/firebasejs/11.6.1/firebase-auth.js';

    // Remplase ak enfòmasyon reyèl konfigirasyon Firebase ou
    const firebaseConfig = {
        apiKey: "AIzaSyCJASbudtFAKF07jDepKiki2iFieGXEE2w",
        authDomain: "quiz-foot-3075f.firebaseapp.com",
        projectId: "quiz-foot-3075f",
        storageBucket: "quiz-foot-3075f.firebasestorage.app",
        messagingSenderId: "358612992669",
        appId: "1:358612992669:web:0f0357c40754fba4c40a74"
    };

    const app = initializeApp(firebaseConfig);
    const auth = getAuth(app);

    const loginForm = document.getElementById('login-form');
    const loginBtn = document.getElementById('login-btn');
    const spinner = document.getElementById('spinner');
    const btnText = document.getElementById('btn-text');
    const errorDiv = document.getElementById('error-message');

    const toggleLoading = (isLoading) => {
        if (isLoading) {
            spinner.classList.remove('hidden');
            btnText.textContent = 'Konekte...';
            loginBtn.disabled = true;
        } else {
            spinner.classList.add('hidden');
            btnText.textContent = 'Konekte';
            loginBtn.disabled = false;
        }
    };

    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        errorDiv.classList.add('hidden');
        toggleLoading(true);
        
        try {
            const userCredential = await signInWithEmailAndPassword(auth, 
                document.getElementById('email').value, 
                document.getElementById('password').value);
            
            const idToken = await userCredential.user.getIdToken();
            
            const response = await fetch('/api/verify_token', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ idToken })
            });

            const data = await response.json();
            if (data.success) {
                window.location.href = '/dashboard';
            } else {
                throw new Error(data.error);
            }
        } catch (error) {
            toggleLoading(false);
            errorDiv.textContent = '❌ ' + (error.message || 'Erè pandan koneksyon');
            if(error.code) {
                // Tradiksyon erè Firebase ki pi komen yo
                if (error.code === 'auth/invalid-email') errorDiv.textContent = '❌ Imèl la pa valid';
                else if (error.code === 'auth/user-disabled') errorDiv.textContent = '❌ Kont sa a enfim';
                else if (error.code === 'auth/user-not-found' || error.code === 'auth/wrong-password') errorDiv.textContent = '❌ Imèl oswa modpas la pa kòrèk';
                else if (error.code === 'auth/too-many-requests') errorDiv.textContent = '❌ Twòp tantativ. Eseye pita.';
            }
            errorDiv.classList.remove('hidden');
        }
    });
</script>
{% endblock %}
""").replace('min-h-screen', '').replace('flex items-center justify-center', '') # Retire body styles nan BASE_HTML pou login

SIGNUP_HTML = BASE_HTML.replace('<body class="text-gray-100', '<body class="text-gray-100').replace('{% block content %}{% endblock %}', """
{% block head_extra %}
<style>
    body { background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); }
</style>
{% endblock %}
{% block content %}
<div class="bg-gray-800 p-8 rounded-xl shadow-2xl max-w-md w-full">
    <h2 class="text-3xl font-bold text-white text-center mb-6">📝 Kreye Kont</h2>
    <div id="error-message" class="hidden bg-red-900 text-red-200 p-3 rounded mb-4"></div>
    <form id="signup-form">
        <input type="text" id="username" placeholder="Non Itilizatè" required minlength="3"
            class="w-full p-3 mb-4 bg-gray-700 text-white rounded border-2 border-gray-600 focus:border-blue-500">
        <input type="email" id="email" placeholder="Email" required 
            class="w-full p-3 mb-4 bg-gray-700 text-white rounded border-2 border-gray-600 focus:border-blue-500">
        <input type="password" id="password" placeholder="Modpas (min 6 karaktè)" required minlength="6"
            class="w-full p-3 mb-4 bg-gray-700 text-white rounded border-2 border-gray-600 focus:border-blue-500">
        <button type="submit" id="signup-btn" class="w-full bg-green-500 hover:bg-green-600 text-white py-3 rounded font-bold flex items-center justify-center relative">
            <span id="btn-text">Enskri Kounye a</span>
            <div id="spinner" class="spinner absolute right-4 hidden"></div>
        </button>
    </form>
    <p class="text-center mt-4 text-gray-300">
        Gen kont deja? <a href="/login" class="text-blue-400 hover:underline">Konekte</a>
    </p>
    <p class="text-center mt-2">
        <a href="/" class="text-gray-400 hover:text-white">← Retounen Akèy</a>
    </p>
</div>

<script type="module">
    import { initializeApp } from 'https://www.gstatic.com/firebasejs/11.6.1/firebase-app.js';
    import { getAuth, createUserWithEmailAndPassword, updateProfile } from 'https://www.gstatic.com/firebasejs/11.6.1/firebase-auth.js';

    // Remplase ak enfòmasyon reyèl konfigirasyon Firebase ou
    const firebaseConfig = {
        apiKey: "AIzaSyCJASbudtFAKF07jDepKiki2iFieGXEE2w",
        authDomain: "quiz-foot-3075f.firebaseapp.com",
        projectId: "quiz-foot-3075f",
        storageBucket: "quiz-foot-3075f.firebasestorage.app",
        messagingSenderId: "358612992669",
        appId: "1:358612992669:web:0f0357c40754fba4c40a74"
    };

    const app = initializeApp(firebaseConfig);
    const auth = getAuth(app);
    
    const signupForm = document.getElementById('signup-form');
    const signupBtn = document.getElementById('signup-btn');
    const spinner = document.getElementById('spinner');
    const btnText = document.getElementById('btn-text');
    const errorDiv = document.getElementById('error-message');

    const toggleLoading = (isLoading) => {
        if (isLoading) {
            spinner.classList.remove('hidden');
            btnText.textContent = 'Enskri...';
            signupBtn.disabled = true;
        } else {
            spinner.classList.add('hidden');
            btnText.textContent = 'Enskri Kounye a';
            signupBtn.disabled = false;
        }
    };

    signupForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        errorDiv.classList.add('hidden');
        toggleLoading(true);
        
        try {
            const username = document.getElementById('username').value.trim();
            const email = document.getElementById('email').value.trim();
            const password = document.getElementById('password').value;
            
            const userCredential = await createUserWithEmailAndPassword(auth, email, password);
            await updateProfile(userCredential.user, { displayName: username });
            
            // Kreye dokiman itilizatè a nan Firestore
            await fetch('/api/create_user', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ uid: userCredential.user.uid, username: username, email: email })
            });

            const idToken = await userCredential.user.getIdToken();
            
            const response = await fetch('/api/verify_token', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ idToken })
            });

            const data = await response.json();
            if (data.success) {
                window.location.href = '/dashboard';
            } else {
                throw new Error(data.error);
            }
        } catch (error) {
            toggleLoading(false);
            let msg = 'Erè pandan enskripsyon';
            if (error.code === 'auth/email-already-in-use') msg = 'Imèl sa a deja anrejistre';
            else if (error.code === 'auth/weak-password') msg = 'Modpas la twò fèb (min 6 karaktè)';
            else if (error.code === 'auth/invalid-email') msg = 'Imèl la pa valid';
            errorDiv.textContent = '❌ ' + msg;
            errorDiv.classList.remove('hidden');
        }
    });
</script>
{% endblock %}
""").replace('min-h-screen', '').replace('flex items-center justify-center', '')

DASHBOARD_HTML = BASE_HTML.replace('{% block content %}{% endblock %}', """
{% block content %}
<div class="bg-gray-800 p-8 rounded-xl mb-8">
    <h1 class="text-4xl font-bold text-green-400 mb-4">👋 Byenveni, {{ user.username }}!</h1>
    <p class="text-xl">
        Estatik Abònman: 
        <span class="{% if user.subscription_status == 'active' %}text-green-400{% else %}text-orange-400{% endif %} font-bold">
            {% if user.subscription_status == 'active' %}✅ PREMIUM AKTIF{% else %}🔓 GRATUIT{% endif %}
        </span>
    </p>
    <div class="grid md:grid-cols-3 gap-4 mt-6">
        <div class="bg-gray-700 p-4 rounded-lg">
            <p class="text-gray-400 text-sm">Nòt Quiz</p>
            <p class="text-3xl font-bold text-green-400">{{ user.quiz_score }}%</p>
        </div>
        <div class="bg-gray-700 p-4 rounded-lg">
            <p class="text-gray-400 text-sm">Match Gade</p>
            <p class="text-3xl font-bold text-blue-400">12</p>
        </div>
        <div class="bg-gray-700 p-4 rounded-lg">
            <p class="text-gray-400 text-sm">Tan Total</p>
            <p class="text-3xl font-bold text-purple-400">8h</p>
        </div>
    </div>
</div>

{% if user.subscription_status != 'active' %}
<div class="bg-orange-900 border-2 border-orange-500 p-6 rounded-xl text-center mb-8">
    <h2 class="text-2xl font-bold mb-4">🔥 Upgrade nan Premium!</h2>
    <p class="mb-4">Gade tout match yo san limit pou sèlman $9.99/mwa</p>
    <a href="/subscription" class="bg-orange-500 hover:bg-orange-600 px-8 py-3 rounded-lg font-bold">Abòne Kounye a</a>
</div>
{% endif %}

<h2 class="text-3xl font-bold mb-6">⚡ Match Disponib</h2>
<div class="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
    <div class="bg-gray-800 p-6 rounded-xl hover:scale-105 transition">
        <h3 class="text-blue-400 font-bold mb-2">Champions League</h3>
        <p class="text-xl font-bold mb-2">REAL MADRID vs FC BARCELONA</p>
        <p class="text-gray-400 text-sm mb-4">📅 25 Oktòb 2025 @ 2:00 PM</p>
        <span class="bg-red-600 text-white px-3 py-1 rounded text-sm">💰 PPV $4.99</span><br>
        <a href="/match_stream/101" class="mt-4 inline-block bg-green-500 hover:bg-green-600 px-6 py-2 rounded-lg">🎥 Gade</a>
    </div>
    <div class="bg-gray-800 p-6 rounded-xl hover:scale-105 transition">
        <h3 class="text-blue-400 font-bold mb-2">Premier League</h3>
        <p class="text-xl font-bold mb-2">MANCHESTER CITY vs LIVERPOOL</p>
        <p class="text-gray-400 text-sm mb-4">📅 26 Oktòb 2025 @ 10:30 AM</p>
        <span class="bg-green-600 text-white px-3 py-1 rounded text-sm">🆓 GRATIS</span><br>
        <a href="/match_stream/102" class="mt-4 inline-block bg-green-500 hover:bg-green-600 px-6 py-2 rounded-lg">🎥 Gade</a>
    </div>
</div>
{% endblock %}
""").replace('min-h-screen', '')

SUBSCRIPTION_HTML = BASE_HTML.replace('{% block content %}{% endblock %}', """
{% block content %}
<main class="container mx-auto px-4 py-12">
    <h1 class="text-4xl font-bold text-center mb-12 text-white">Chwazi Plan Abònman ou</h1>
    
    <div class="grid md:grid-cols-2 gap-8 max-w-4xl mx-auto">
        <div class="bg-gray-800 border-4 border-orange-500 rounded-xl p-8 text-center">
            <h2 class="text-2xl font-bold text-orange-500 mb-4">ABÒNMAN PREMIUM</h2>
            <p class="text-5xl font-bold text-green-400 mb-6">$9.99<span class="text-xl">/mwa</span></p>
            <ul class="text-left mb-8 space-y-2">
                <li>✅ Aksè a TOUT Match yo Live</li>
                <li>✅ Difizyon HD san limit</li>
                <li>✅ Achiv Match (Replay)</li>
                <li>✅ Patisipasyon nan Konkou</li>
            </ul>
            <form id="premium-form" action="{{ url_for('process_payment') }}" method="POST">
                <input type="hidden" name="plan" value="monthly_premium">
                <button type="submit" id="premium-btn" class="w-full bg-orange-500 hover:bg-orange-600 py-3 rounded-lg font-bold text-white flex items-center justify-center relative">
                    <span id="btn-text-premium">Kòmanse Abònman an</span>
                    <div id="spinner-premium" class="spinner absolute right-4 hidden"></div>
                </button>
            </form>
        </div>
        
        <div class="bg-gray-800 border-4 border-blue-500 rounded-xl p-8 text-center">
            <h2 class="text-2xl font-bold text-blue-400 mb-4">PAY-PER-VIEW (PPV)</h2>
            <p class="text-5xl font-bold text-blue-400 mb-6">$4.99<span class="text-xl">/match</span></p>
            <ul class="text-left mb-8 space-y-2">
                <li>✅ Aksè a sèlman 1 match</li>
                <li>✅ Pa angaje ou</li>
                <li>❌ Pa gen aksè a achiv</li>
                <li>❌ Pa patisipe nan konkou</li>
            </ul>
            <a href="/dashboard" class="block w-full bg-blue-500 hover:bg-blue-600 py-3 rounded-lg font-bold text-white">
                Chwazi Match PPV
            </a>
        </div>
    </div>
</main>
<script>
    document.getElementById('premium-form').addEventListener('submit', function() {
        const btn = document.getElementById('premium-btn');
        const spinner = document.getElementById('spinner-premium');
        const text = document.getElementById('btn-text-premium');
        spinner.classList.remove('hidden');
        text.textContent = 'Ap trete...';
        btn.disabled = true;
    });
</script>
{% endblock %}
""").replace('min-h-screen', '')

BUY_PPV_HTML = BASE_HTML.replace('{% block content %}{% endblock %}', """
{% block head_extra %}
<style>
    body { background: linear-gradient(135deg, #121212 0%, #1a1a2e 100%); }
</style>
{% endblock %}
{% block content %}
<main class="container mx-auto px-4 py-12">
    <div class="max-w-2xl mx-auto bg-gray-800 p-8 rounded-xl border-t-4 border-orange-500">
        <h2 class="text-3xl font-bold text-center mb-6">Achte Aksè Match PPV</h2>
        <h3 class="text-2xl text-blue-400 text-center mb-2">{{ match_name }}</h3>
        <p class="text-gray-400 text-center mb-6">{{ league }} | {{ match_date }}</p>
        <p class="text-5xl font-bold text-green-400 text-center mb-8">Pri Total: ${{ ppv_price }}</p>
        
        <form id="ppv-form" action="{{ url_for('process_ppv_purchase', match_id=match_id) }}" method="POST">
            <input type="hidden" name="payment_method" value="card">
            
            <div class="mb-6">
                <label class="block text-gray-300 mb-2">Non sou Kat la</label>
                <input type="text" name="card_holder_name" required 
                    class="w-full p-3 bg-gray-700 rounded border-2 border-gray-600 focus:border-blue-500">
            </div>
            
            <div class="mb-6">
                <label class="block text-gray-300 mb-2">Nimewo Kat (16 chif)</label>
                <input type="text" name="card_number" required 
                    class="w-full p-3 bg-gray-700 rounded border-2 border-gray-600 focus:border-blue-500">
            </div>
            
            <div class="grid grid-cols-2 gap-4 mb-6">
                <div>
                    <label class="block text-gray-300 mb-2">MM/YY</label>
                    <input type="text" name="expiry" required 
                        class="w-full p-3 bg-gray-700 rounded border-2 border-gray-600 focus:border-blue-500">
                </div>
                <div>
                    <label class="block text-gray-300 mb-2">CVV</label>
                    <input type="text" name="cvv" required 
                        class="w-full p-3 bg-gray-700 rounded border-2 border-gray-600 focus:border-blue-500">
                </div>
            </div>
            
            <button type="submit" id="ppv-btn" class="w-full bg-orange-500 hover:bg-orange-600 text-white py-4 rounded-lg font-bold text-lg flex items-center justify-center relative">
                <span id="btn-text-ppv">Peye ${{ ppv_price }} epi Jwenn Aksè</span>
                <div id="spinner-ppv" class="spinner absolute right-4 hidden"></div>
            </button>
        </form>
        
        <p class="text-center mt-6">
            <a href="/" class="text-blue-400 hover:underline">Retounen nan Akèy</a>
        </p>
    </div>
</main>
<script>
    document.getElementById('ppv-form').addEventListener('submit', function() {
        const btn = document.getElementById('ppv-btn');
        const spinner = document.getElementById('spinner-ppv');
        const text = document.getElementById('btn-text-ppv');
        spinner.classList.remove('hidden');
        text.textContent = 'Ap trete peman...';
        btn.disabled = true;
    });
</script>
{% endblock %}
""")

MATCH_STREAM_HTML = BASE_HTML.replace('{% block content %}{% endblock %}', """
{% block content %}
<main class="container mx-auto px-4 py-8">
    <h1 class="text-3xl font-bold mb-2">{{ match_name }}</h1>
    <p class="text-gray-400 mb-6">{{ league }} | {{ match_date }}</p>
    
    {% if has_access %}
    <div class="video-container rounded-xl overflow-hidden mb-8 flex items-center justify-center">
        <div class="text-center">
            <p class="text-2xl mb-4">🎥 LIVE STREAM</p>
            <p class="text-gray-400">Stream vidéo a ta dwe parèt isit la</p>
        </div>
    </div>
    
    <div class="bg-gray-800 p-6 rounded-xl">
        <h2 class="text-2xl font-bold mb-4">📊 Enfòmasyon Match</h2>
        <div class="grid md:grid-cols-2 gap-4">
            <div>
                <h3 class="font-bold text-blue-400 mb-2">Ekip Lakay</h3>
                <p class="text-lg">{{ match_name.split(' vs ')[0] }}</p>
            </div>
            <div>
                <h3 class="font-bold text-orange-400 mb-2">Ekip Vizitè</h3>
                <p class="text-lg">{{ match_name.split(' vs ')[1] if ' vs ' in match_name else 'N/A' }}</p>
            </div>
        </div>
    </div>
    {% else %}
    <div class="bg-red-900 border-4 border-red-500 p-8 rounded-xl text-center">
        <h2 class="text-3xl font-bold mb-4">⚠️ Aksè Refize!</h2>
        <p class="text-lg mb-6">Ou pa gen aksè a match sa a. Chwazi yon opsyon:</p>
        <div class="flex gap-4 justify-center flex-wrap">
            <a href="{{ url_for('show_ppv_purchase', match_id=match_id) }}" 
               class="bg-orange-500 hover:bg-orange-600 px-6 py-3 rounded-lg font-bold">
                Achte PPV (${{ ppv_price }})
            </a>
            <a href="/subscription" class="bg-blue-500 hover:bg-blue-600 px-6 py-3 rounded-lg font-bold">
                Abòne Premium ($9.99/mwa)
            </a>
        </div>
    </div>
    {% endif %}
</main>
{% endblock %}
""").replace('min-h-screen', '')

SUCCESS_PAYMENT_HTML = BASE_HTML.replace('<body class="text-gray-100', '<body class="text-gray-100').replace('{% block content %}{% endblock %}', """
{% block head_extra %}
<style>
    body { background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); }
    @keyframes checkmark {
        0% { transform: scale(0); }
        50% { transform: scale(1.2); }
        100% { transform: scale(1); }
    }
    .check-animated { animation: checkmark 0.6s ease-out; }
</style>
{% endblock %}
{% block content %}
<div class="max-w-2xl mx-auto bg-gray-800 p-12 rounded-2xl border-4 border-green-500 text-center">
    <div class="text-6xl text-green-400 mb-6 check-animated">✅</div>
    <h2 class="text-4xl font-bold text-green-400 mb-6">Felisitasyon!</h2>
    <div class="bg-green-900 bg-opacity-30 p-6 rounded-xl mb-6">
        <p class="text-xl font-semibold">{{ message if message else 'Peman ou an reyisi avèk siksè!' }}</p>
    </div>
    <p class="text-gray-300 mb-8">🎉 Ou gen aksè kounye a. Aksè ou aktif imedyatman.</p>
    <a href="/dashboard" class="inline-block bg-orange-500 hover:bg-orange-600 text-white px-8 py-4 rounded-lg font-bold text-xl">
        🏠 Ale sou Dashboard
    </a>
    {% if match_id %}
    <a href="{{ url_for('match_stream', match_id=match_id) }}" class="inline-block bg-green-500 hover:bg-green-600 text-white px-8 py-4 rounded-lg font-bold text-xl ml-4">
        🎥 Gade Match la
    </a>
    {% endif %}
</div>
{% endblock %}
""").replace('min-h-screen', '').replace('flex items-center justify-center', '')

ERROR_PAYMENT_HTML = BASE_HTML.replace('<body class="text-gray-100', '<body class="text-gray-100').replace('{% block content %}{% endblock %}', """
{% block head_extra %}
<style>
    body { background: linear-gradient(135deg, #1e1e2d 0%, #1a1a2e 100%); }
    @keyframes shake {
        0%, 100% { transform: translateX(0); }
        25% { transform: translateX(-10px); }
        75% { transform: translateX(10px); }
    }
    .shake-animated { animation: shake 0.6s ease-out; }
</style>
{% endblock %}
{% block content %}
<div class="max-w-2xl mx-auto bg-gray-800 p-12 rounded-2xl border-4 border-red-500 text-center shake-animated">
    <div class="text-6xl text-red-500 mb-6">❌</div>
    <h2 class="text-4xl font-bold text-red-500 mb-6">Echèk Peman!</h2>
    <div class="bg-red-900 bg-opacity-30 p-6 rounded-xl mb-6">
        <p class="text-xl font-semibold">{{ error_message if error_message else 'Peman ou an pa reyisi. Tanpri eseye ankò.' }}</p>
    </div>
    <p class="text-gray-300 mb-8">Verifye detay peman ou yo epi eseye ankò.</p>
    {% if match_id %}
    <a href="{{ url_for('show_ppv_purchase', match_id=match_id) }}" class="inline-block bg-orange-500 hover:bg-orange-600 text-white px-8 py-4 rounded-lg font-bold text-xl">
        🔄 Eseye Ankò
    </a>
    {% else %}
    <a href="/" class="inline-block bg-orange-500 hover:bg-orange-600 text-white px-8 py-4 rounded-lg font-bold text-xl">
        🏠 Retounen Akèy
    </a>
    {% endif %}
</div>
{% endblock %}
""").replace('min-h-screen', '').replace('flex items-center justify-center', '')

FORGOT_PASSWORD_HTML = BASE_HTML.replace('<body class="text-gray-100', '<body class="text-gray-100').replace('{% block content %}{% endblock %}', """
{% block head_extra %}
<style>
    body { background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); }
</style>
{% endblock %}
{% block content %}
<div class="bg-gray-800 p-8 rounded-xl shadow-2xl max-w-md w-full">
    <h2 class="text-3xl font-bold text-white text-center mb-6">🔑 Bliye Modpas</h2>
    <p class="text-gray-400 text-center mb-6">Antre adrès imèl ou pou n voye yon lyen pou w ka kreye yon nouvo modpas.</p>
    <div id="message" class="hidden bg-red-900 text-red-200 p-3 rounded mb-4"></div>
    <form id="forgot-password-form">
        <input type="email" id="email" placeholder="Email" required 
            class="w-full p-3 mb-4 bg-gray-700 text-white rounded border-2 border-gray-600 focus:border-blue-500">
        <button type="submit" id="reset-btn" class="w-full bg-red-600 hover:bg-red-700 text-white py-3 rounded font-bold flex items-center justify-center relative">
            <span id="btn-text">Voye Lyen Reset</span>
            <div id="spinner" class="spinner absolute right-4 hidden"></div>
        </button>
    </form>
    <p class="text-center mt-4">
        <a href="/login" class="text-blue-400 hover:underline">← Retounen Konekte</a>
    </p>
</div>

<script type="module">
    import { initializeApp } from 'https://www.gstatic.com/firebasejs/11.6.1/firebase-app.js';
    import { getAuth, sendPasswordResetEmail } from 'https://www.gstatic.com/firebasejs/11.6.1/firebase-auth.js';

    // Remplase ak enfòmasyon reyèl konfigirasyon Firebase ou
    const firebaseConfig = {
        apiKey: "AIzaSyCJASbudtFAKF07jDepKiki2iFieGXEE2w",
        authDomain: "quiz-foot-3075f.firebaseapp.com",
        projectId: "quiz-foot-3075f",
        storageBucket: "quiz-foot-3075f.firebasestorage.app",
        messagingSenderId: "358612992669",
        appId: "1:358612992669:web:0f0357c40754fba4c40a74"
    };

    const app = initializeApp(firebaseConfig);
    const auth = getAuth(app);

    const form = document.getElementById('forgot-password-form');
    const resetBtn = document.getElementById('reset-btn');
    const spinner = document.getElementById('spinner');
    const btnText = document.getElementById('btn-text');
    const messageDiv = document.getElementById('message');

    const toggleLoading = (isLoading) => {
        if (isLoading) {
            spinner.classList.remove('hidden');
            btnText.textContent = 'Ap voye...';
            resetBtn.disabled = true;
        } else {
            spinner.classList.add('hidden');
            btnText.textContent = 'Voye Lyen Reset';
            resetBtn.disabled = false;
        }
    };

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        messageDiv.classList.add('hidden');
        messageDiv.classList.remove('bg-green-900', 'bg-red-900', 'text-green-200', 'text-red-200');
        toggleLoading(true);
        
        const email = document.getElementById('email').value.trim();

        try {
            await sendPasswordResetEmail(auth, email);
            messageDiv.textContent = '✅ Yon lyen pou kreye nouvo modpas voye nan: ' + email;
            messageDiv.classList.add('bg-green-900', 'text-green-200');
            document.getElementById('email').value = '';
        } catch (error) {
            let msg = 'Erè pandan voye imèl la';
            if (error.code === 'auth/invalid-email') msg = 'Imèl la pa valid';
            else if (error.code === 'auth/user-not-found') msg = 'Pa gen kont ak imèl sa a';
            messageDiv.textContent = '❌ ' + msg;
            messageDiv.classList.add('bg-red-900', 'text-red-200');
        } finally {
            toggleLoading(false);
            messageDiv.classList.remove('hidden');
        }
    });
</script>
{% endblock %}
""").replace('min-h-screen', '').replace('flex items-center justify-center', '')

# --- Fonksyon Sipò ---
def render_base_template_string(template, title, is_centered=False, **kwargs):
    """
    Rann yon modèl HTML anndan BASE_HTML la, epi ajoute header/footer
    ak enfòmasyon sesyon yo.
    """
    logged_in = 'uid' in session
    return render_template_string(
        BASE_HTML,
        content=template,
        title=title,
        logged_in=logged_in,
        is_centered=is_centered,
        **kwargs
    )

# ----------------- DECORATOR -----------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'uid' not in session:
            print(f"⚠️ Aksè refize: {request.path}")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ----------------- ROUTES -----------------

@app.route('/')
def index():
    logged_in = 'uid' in session
    return render_template_string(INDEX_HTML, title="Akèy", logged_in=logged_in)

@app.route('/login')
def login():
    if 'uid' in session:
        return redirect(url_for('dashboard'))
    return render_template_string(LOGIN_HTML, title="Konekte", is_centered=True)

@app.route('/signup')
def signup():
    if 'uid' in session:
        return redirect(url_for('dashboard'))
    return render_template_string(SIGNUP_HTML, title="Enskri", is_centered=True)

@app.route('/forgot_password')
def forgot_password():
    if 'uid' in session:
        return redirect(url_for('dashboard'))
    return render_template_string(FORGOT_PASSWORD_HTML, title="Bliye Modpas", is_centered=True)

@app.route('/logout')
def logout():
    session.clear()
    print(f"👋 Dekonekte")
    return redirect(url_for('index'))

@app.route('/api/verify_token', methods=['POST', 'OPTIONS'])
def verify_token():
    if request.method == 'OPTIONS':
        response = jsonify({'success': True})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST')
        return response

    try:
        data = request.get_json()
        id_token = data.get('idToken')
        
        if not id_token:
            return jsonify({'success': False, 'error': 'Token manke'}), 400

        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']
        email = decoded_token.get('email', '')
        
        print(f"✅ Token verifye: {email}")

        # Jwenn dokiman itilizatè a nan Firestore
        user_ref = db.collection('users').document(uid)
        user_doc = user_ref.get()

        if not user_doc.exists:
            # Ka sa a pa ta dwe rive si yo te itilize paj signup la
            # Kreyasyon yon dokiman default si li manke
            username = decoded_token.get('name', email.split('@')[0])
            user_data = {
                'uid': uid,
                'email': email,
                'username': username,
                'subscription_status': 'free',
                'quiz_score': 0,
                'purchased_ppv': [],
                'created_at': firestore.SERVER_TIMESTAMP
            }
            user_ref.set(user_data)
            print(f"⚠️ Kreyasyon dokiman Firestore pou: {email}")
        else:
            user_data = user_doc.to_dict()

        # Mete enfòmasyon itilizatè a nan sesyon Flask la
        session.permanent = True
        session['uid'] = uid
        session['email'] = email
        session['username'] = user_data.get('username', email.split('@')[0])
        
        return jsonify({'success': True, 'uid': uid})

    except Exception as e:
        print(f"❌ Erè Verifikasyon Token: {str(e)}")
        # Netwaye sesyon an ka gen erè
        session.clear()
        return jsonify({'success': False, 'error': str(e)}), 401

@app.route('/api/create_user', methods=['POST'])
def create_user_doc():
    """Endpoint API pou kreye dokiman itilizatè a nan Firestore apre enskripsyon"""
    try:
        data = request.get_json()
        uid = data.get('uid')
        username = data.get('username')
        email = data.get('email')

        if not uid or not username or not email:
            return jsonify({'success': False, 'error': 'Done manke pou kreyasyon itilizatè'}), 400

        user_data = {
            'uid': uid,
            'email': email,
            'username': username,
            'subscription_status': 'free',
            'quiz_score': 0,
            'purchased_ppv': [],
            'created_at': firestore.SERVER_TIMESTAMP
        }
        db.collection('users').document(uid).set(user_data)
        print(f"✅ Dokiman itilizatè kreye: {email}")
        return jsonify({'success': True})
    except Exception as e:
        print(f"❌ Erè kreyasyon dokiman Firestore: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/dashboard')
@login_required
def dashboard():
    uid = session.get('uid')
    try:
        user_doc = db.collection('users').document(uid).get()
        user_data = user_doc.to_dict() if user_doc.exists else {}
        
        # Done default si yon bagay manke
        user = {
            'username': session.get('username', 'Itilizatè'),
            'subscription_status': user_data.get('subscription_status', 'free'),
            'quiz_score': user_data.get('quiz_score', 0),
            'purchased_ppv': user_data.get('purchased_ppv', []),
        }
        
        return render_template_string(DASHBOARD_HTML, title="Dashboard", user=user)

    except Exception as e:
        print(f"❌ Erè nan dashboard: {str(e)}")
        # Erè Firebase oswa koneksyon -> Dekonekte
        session.clear()
        return redirect(url_for('login'))

@app.route('/subscription')
@login_required
def subscription():
    return render_template_string(SUBSCRIPTION_HTML, title="Abònman")

@app.route('/match_stream/<match_id>')
@login_required
def match_stream(match_id):
    if match_id not in MATCH_DATABASE:
        return redirect(url_for('dashboard')) # Match pa egziste

    match_info = MATCH_DATABASE[match_id]
    uid = session.get('uid')

    # 1. Tcheke si Premium aktif
    user_doc = db.collection('users').document(uid).get()
    user_data = user_doc.to_dict() if user_doc.exists else {}
    subscription_status = user_data.get('subscription_status', 'free')

    has_access = subscription_status == 'active'

    # 2. Tcheke si PPV achte
    if not has_access and match_info.get('is_ppv'):
        purchased_ppv = user_data.get('purchased_ppv', [])
        if match_id in purchased_ppv:
            has_access = True
            
    # 3. Match gratis
    if not match_info.get('is_ppv'):
        has_access = True

    return render_template_string(MATCH_STREAM_HTML, 
                                  title=match_info['name'],
                                  match_name=match_info['name'],
                                  league=match_info['league'],
                                  match_date=match_info['date'],
                                  ppv_price=match_info['ppv_price'],
                                  match_id=match_id,
                                  has_access=has_access)

@app.route('/buy_ppv/<match_id>')
@login_required
def show_ppv_purchase(match_id):
    if match_id not in MATCH_DATABASE or not MATCH_DATABASE[match_id].get('is_ppv'):
        return redirect(url_for('dashboard'))
    
    match_info = MATCH_DATABASE[match_id]
    
    return render_template_string(BUY_PPV_HTML, 
                                  title=f"Achte PPV - {match_info['name']}",
                                  match_name=match_info['name'],
                                  league=match_info['league'],
                                  match_date=match_info['date'],
                                  ppv_price=match_info['ppv_price'],
                                  match_id=match_id)

@app.route('/process_ppv_purchase/<match_id>', methods=['POST'])
@login_required
def process_ppv_purchase(match_id):
    if match_id not in MATCH_DATABASE or not MATCH_DATABASE[match_id].get('is_ppv'):
        return redirect(url_for('dashboard'))
    
    # Similasyon pwosesis peman
    time.sleep(2) # Simile latans peman
    
    # Similasyon yon erè peman sou kat ki gen nimewo "1111"
    card_number = request.form.get('card_number', '')
    if '1111' in card_number:
         return render_template_string(ERROR_PAYMENT_HTML, 
                                       error_message="Peman an echwe. Nimewo kat la pa valid (similasyon).",
                                       match_id=match_id)

    try:
        # Mete ajou Firestore
        uid = session['uid']
        user_ref = db.collection('users').document(uid)
        
        # Tcheke si li deja achte
        user_doc = user_ref.get()
        purchased_ppv = user_doc.to_dict().get('purchased_ppv', [])
        
        if match_id not in purchased_ppv:
            user_ref.update({
                'purchased_ppv': firestore.ArrayUnion([match_id])
            })
            print(f"✅ PPV Match {match_id} achte pou {session['email']}")
        
        return render_template_string(SUCCESS_PAYMENT_HTML, 
                                      message=f"Ou achte aksè a match {MATCH_DATABASE[match_id]['name']} pou ${MATCH_DATABASE[match_id]['ppv_price']}!",
                                      match_id=match_id)
    
    except Exception as e:
        print(f"❌ Erè pandan achte PPV: {str(e)}")
        return render_template_string(ERROR_PAYMENT_HTML, 
                                      error_message="Erè sèvè pandan anrejistreman achte a.",
                                      match_id=match_id)

@app.route('/process_payment', methods=['POST'])
@login_required
def process_payment():
    plan = request.form.get('plan')
    
    if plan != 'monthly_premium':
        return redirect(url_for('subscription'))

    # Similasyon pwosesis peman
    time.sleep(2) # Simile latans peman
    
    try:
        # Mete ajou Firestore
        uid = session['uid']
        user_ref = db.collection('users').document(uid)
        
        user_ref.update({
            'subscription_status': 'active',
            'subscription_start': firestore.SERVER_TIMESTAMP,
            'subscription_end': datetime.now() + timedelta(days=30)
        })
        print(f"✅ Abònman Premium aktive pou {session['email']}")
        
        return render_template_string(SUCCESS_PAYMENT_HTML, 
                                      message="Abònman Premium ou an aktive! Jwi tout match yo!",
                                      match_id=None)
    
    except Exception as e:
        print(f"❌ Erè pandan abònman Premium: {str(e)}")
        return render_template_string(ERROR_PAYMENT_HTML, 
                                      error_message="Erè sèvè pandan anrejistreman abònman an.",
                                      match_id=None)


if __name__ == '__main__':
    # Ajoute default style body nan modèl ki santre yo
    LOGIN_HTML = LOGIN_HTML.replace('min-h-screen', 'min-h-screen').replace('flex items-center justify-center', 'flex items-center justify-center')
    SIGNUP_HTML = SIGNUP_HTML.replace('min-h-screen', 'min-h-screen').replace('flex items-center justify-center', 'flex items-center justify-center')
    FORGOT_PASSWORD_HTML = FORGOT_PASSWORD_HTML.replace('min-h-screen', 'min-h-screen').replace('flex items-center justify-center', 'flex items-center justify-center')
    SUCCESS_PAYMENT_HTML = SUCCESS_PAYMENT_HTML.replace('min-h-screen', 'min-h-screen').replace('flex items-center justify-center', 'flex items-center justify-center')
    ERROR_PAYMENT_HTML = ERROR_PAYMENT_HTML.replace('min-h-screen', 'min-h-screen').replace('flex items-center justify-center', 'flex items-center justify-center')
    
    # Retire pati 'body' nan INDEX_HTML ki deja genyen style 'body' li
    INDEX_HTML = INDEX_HTML.replace('<body class="text-gray-100">', '').replace('</body>', '')
    DASHBOARD_HTML = DASHBOARD_HTML.replace('<body class="text-gray-100">', '').replace('</body>', '')
    SUBSCRIPTION_HTML = SUBSCRIPTION_HTML.replace('<body class="text-gray-100">', '').replace('</body>', '')
    BUY_PPV_HTML = BUY_PPV_HTML.replace('<body class="text-gray-100">', '').replace('</body>', '')
    MATCH_STREAM_HTML = MATCH_STREAM_HTML.replace('<body class="text-gray-100">', '').replace('</body>', '')
    
    app.run(debug=True, port=5000)