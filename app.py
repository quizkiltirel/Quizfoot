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

# Konfigirasyon CORS sekirize
ALLOWED_ORIGINS = [
    'https://quizfoot.onrender.com',
    'http://localhost:5000',
    'http://127.0.0.1:5000'
]

CORS(app, 
     supports_credentials=True, 
     resources={r"/*": {
         "origins": ALLOWED_ORIGINS,
         "methods": ["GET", "POST", "OPTIONS"],
         "allow_headers": ["Content-Type", "Authorization"]
     }})

# Kle sekrè - ENPÒTAN: Chanje sa a ak yon kle random pou pwodiksyon
import os
app.secret_key = os.environ.get('SECRET_KEY', 'Yon_Kle_Sekre_Tres_Long_E_Konplike_Pou_Quiz_Foot_2024_Sekirize')

# Konfigirasyon sekirite sesyon
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
app.config['SESSION_COOKIE_SECURE'] = True  # Sèlman HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Pa aksesib via JavaScript
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Pwoteksyon kont CSRF

# Limit gwosè resevwa nan request
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# ----------------- BAZ DONE MATCH -----------------
MATCH_DATABASE = {
    "101": {"name": "REAL MADRID vs FC BARCELONA", "league": "Liga Chanpyon", "date": "25 Oktòb 2025 @ 2:00 PM", "ppv_price": 4.99, "is_ppv": True},
    "102": {"name": "MANCHESTER CITY vs LIVERPOOL FC", "league": "Premier League", "date": "26 Oktòb 2025 @ 10:30 AM", "ppv_price": 0.00, "is_ppv": False},
    "103": {"name": "JUVENTUS vs INTER MILAN", "league": "Serie A", "date": "26 Oktòb 2025 @ 4:45 PM", "ppv_price": 2.99, "is_ppv": True},
    "104": {"name": "PSG vs MARSEILLE", "league": "Ligue 1", "date": "27 Oktòb 2025 @ 1:00 PM", "ppv_price": 0.00, "is_ppv": False}
}

# ----------------- HTML TEMPLATES -----------------

INDEX_HTML = """<!DOCTYPE html>
<html lang="ht">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Akèy - Quiz Foot</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%); min-height: 100vh; }
        .hero { background: linear-gradient(rgba(15, 12, 41, 0.8), rgba(15, 12, 41, 0.9)); }
    </style>
</head>
<body class="text-gray-100">
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
    
    <footer class="bg-gray-800 text-center py-6 mt-12">
        <p class="text-gray-400">&copy; 2025 Quiz Foot. Tout Dwa Rezève.</p>
    </footer>
</body>
</html>"""

LOGIN_HTML = """<!DOCTYPE html>
<html lang="ht">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Konekte - Quiz Foot</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { 
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); 
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
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
</head>
<body class="text-gray-100">
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
                    if (error.code === 'auth/invalid-email') errorDiv.textContent = '❌ Imèl la pa valid';
                    else if (error.code === 'auth/user-disabled') errorDiv.textContent = '❌ Kont sa a enfim';
                    else if (error.code === 'auth/user-not-found' || error.code === 'auth/wrong-password') errorDiv.textContent = '❌ Imèl oswa modpas la pa kòrèk';
                    else if (error.code === 'auth/too-many-requests') errorDiv.textContent = '❌ Twòp tantativ. Eseye pita.';
                }
                errorDiv.classList.remove('hidden');
            }
        });
    </script>
</body>
</html>"""

SIGNUP_HTML = """<!DOCTYPE html>
<html lang="ht">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Enskri - Quiz Foot</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { 
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); 
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
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
</head>
<body class="text-gray-100">
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
</body>
</html>"""

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="ht">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard - Quiz Foot</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%); min-height: 100vh; }
    </style>
</head>
<body class="text-gray-100">
    <header class="bg-gray-800 shadow-lg px-6 py-4 flex justify-between items-center">
        <div class="text-2xl font-bold text-orange-500">⚽ QUIZ FOOT</div>
        <nav class="flex gap-4">
            <a href="/" class="text-gray-200 hover:text-white">Akèy</a>
            <a href="/dashboard" class="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-lg">Dashboard</a>
            <a href="/logout" class="bg-red-600 hover:bg-red-700 px-4 py-2 rounded-lg">Dekonekte</a>
        </nav>
    </header>

    <main class="container mx-auto px-4 py-8">
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
    </main>
    
    <footer class="bg-gray-800 text-center py-6 mt-12">
        <p class="text-gray-400">&copy; 2025 Quiz Foot. Tout Dwa Rezève.</p>
    </footer>
</body>
</html>"""

SUBSCRIPTION_HTML = """<!DOCTYPE html>
<html lang="ht">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Abònman - Quiz Foot</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%); min-height: 100vh; }
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
</head>
<body class="text-gray-100">
    <header class="bg-gray-800 shadow-lg px-6 py-4 flex justify-between items-center">
        <div class="text-2xl font-bold text-orange-500">⚽ QUIZ FOOT</div>
        <nav class="flex gap-4">
            <a href="/" class="text-gray-200 hover:text-white">Akèy</a>
            <a href="/dashboard" class="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-lg">Dashboard</a>
            <a href="/logout" class="bg-red-600 hover:bg-red-700 px-4 py-2 rounded-lg">Dekonekte</a>
        </nav>
    </header>

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
                <form id="premium-form" action="/process_payment" method="POST">
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
    
    <footer class="bg-gray-800 text-center py-6 mt-12">
        <p class="text-gray-400">&copy; 2025 Quiz Foot. Tout Dwa Rezève.</p>
    </footer>
    
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
</body>
</html>"""

BUY_PPV_HTML = """<!DOCTYPE html>
<html lang="ht">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Achte PPV - Quiz Foot</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { background: linear-gradient(135deg, #121212 0%, #1a1a2e 100%); min-height: 100vh; }
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
</head>
<body class="text-gray-100">
    <header class="bg-gray-800 shadow-lg px-6 py-4 flex justify-between items-center">
        <div class="text-2xl font-bold text-orange-500">⚽ QUIZ FOOT</div>
        <nav class="flex gap-4">
            <a href="/" class="text-gray-200 hover:text-white">Akèy</a>
            <a href="/dashboard" class="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-lg">Dashboard</a>
            <a href="/logout" class="bg-red-600 hover:bg-red-700 px-4 py-2 rounded-lg">Dekonekte</a>
        </nav>
    </header>

    <main class="container mx-auto px-4 py-12">
        <div class="max-w-2xl mx-auto bg-gray-800 p-8 rounded-xl border-t-4 border-orange-500">
            <h2 class="text-3xl font-bold text-center mb-6">Achte Aksè Match PPV</h2>
            <h3 class="text-2xl text-blue-400 text-center mb-2">{{ match_name }}</h3>
            <p class="text-gray-400 text-center mb-6">{{ league }} | {{ match_date }}</p>
            <p class="text-5xl font-bold text-green-400 text-center mb-8">Pri Total: ${{ ppv_price }}</p>
            
            <form id="ppv-form" action="/process_ppv_purchase/{{ match_id }}" method="POST">
                <input type="hidden" name="payment_method" value="card">
                
                <div class="mb-6">
                    <label class="block text-gray-300 mb-2">Non sou Kat la</label>
                    <input type="text" name="card_holder_name" required 
                        class="w-full p-3 bg-gray-700 rounded border-2 border-gray-600 focus:border-blue-500 text-white">
                </div>
                
                <div class="mb-6">
                    <label class="block text-gray-300 mb-2">Nimewo Kat (16 chif)</label>
                    <input type="text" name="card_number" required 
                        class="w-full p-3 bg-gray-700 rounded border-2 border-gray-600 focus:border-blue-500 text-white">
                </div>
                
                <div class="grid grid-cols-2 gap-4 mb-6">
                    <div>
                        <label class="block text-gray-300 mb-2">MM/YY</label>
                        <input type="text" name="expiry" required 
                            class="w-full p-3 bg-gray-700 rounded border-2 border-gray-600 focus:border-blue-500 text-white">
                    </div>
                    <div>
                        <label class="block text-gray-300 mb-2">CVV</label>
                        <input type="text" name="cvv" required 
                            class="w-full p-3 bg-gray-700 rounded border-2 border-gray-600 focus:border-blue-500 text-white">
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
    
    <footer class="bg-gray-800 text-center py-6 mt-12">
        <p class="text-gray-400">&copy; 2025 Quiz Foot. Tout Dwa Rezève.</p>
    </footer>
    
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
</body>
</html>"""

MATCH_STREAM_HTML = """<!DOCTYPE html>
<html lang="ht">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ match_name }} - Quiz Foot</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%); min-height: 100vh; }
        .video-container { background: #000; min-height: 400px; }
    </style>
</head>
<body class="text-gray-100">
    <header class="bg-gray-800 shadow-lg px-6 py-4 flex justify-between items-center">
        <div class="text-2xl font-bold text-orange-500">⚽ QUIZ FOOT</div>
        <nav class="flex gap-4">
            <a href="/" class="text-gray-200 hover:text-white">Akèy</a>
            <a href="/dashboard" class="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-lg">Dashboard</a>
            <a href="/logout" class="bg-red-600 hover:bg-red-700 px-4 py-2 rounded-lg">Dekonekte</a>
        </nav>
    </header>

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
                <a href="/buy_ppv/{{ match_id }}" 
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
    
    <footer class="bg-gray-800 text-center py-6 mt-12">
        <p class="text-gray-400">&copy; 2025 Quiz Foot. Tout Dwa Rezève.</p>
    </footer>
</body>
</html>"""

SUCCESS_PAYMENT_HTML = """<!DOCTYPE html>
<html lang="ht">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Siksè - Quiz Foot</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { 
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); 
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        @keyframes checkmark {
            0% { transform: scale(0); }
            50% { transform: scale(1.2); }
            100% { transform: scale(1); }
        }
        .check-animated { animation: checkmark 0.6s ease-out; }
    </style>
</head>
<body class="text-gray-100">
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
        <a href="/match_stream/{{ match_id }}" class="inline-block bg-green-500 hover:bg-green-600 text-white px-8 py-4 rounded-lg font-bold text-xl ml-4">
            🎥 Gade Match la
        </a>
        {% endif %}
    </div>
</body>
</html>"""

ERROR_PAYMENT_HTML = """<!DOCTYPE html>
<html lang="ht">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Erè - Quiz Foot</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { 
            background: linear-gradient(135deg, #1e1e2d 0%, #1a1a2e 100%); 
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        @keyframes shake {
            0%, 100% { transform: translateX(0); }
            25% { transform: translateX(-10px); }
            75% { transform: translateX(10px); }
        }
        .shake-animated { animation: shake 0.6s ease-out; }
    </style>
</head>
<body class="text-gray-100">
    <div class="max-w-2xl mx-auto bg-gray-800 p-12 rounded-2xl border-4 border-red-500 text-center shake-animated">
        <div class="text-6xl text-red-500 mb-6">❌</div>
        <h2 class="text-4xl font-bold text-red-500 mb-6">Echèk Peman!</h2>
        <div class="bg-red-900 bg-opacity-30 p-6 rounded-xl mb-6">
            <p class="text-xl font-semibold">{{ error_message if error_message else 'Peman ou an pa reyisi. Tanpri eseye ankò.' }}</p>
        </div>
        <p class="text-gray-300 mb-8">Verifye detay peman ou yo epi eseye ankò.</p>
        {% if match_id %}
        <a href="/buy_ppv/{{ match_id }}" class="inline-block bg-orange-500 hover:bg-orange-600 text-white px-8 py-4 rounded-lg font-bold text-xl">
            🔄 Eseye Ankò
        </a>
        {% else %}
        <a href="/" class="inline-block bg-orange-500 hover:bg-orange-600 text-white px-8 py-4 rounded-lg font-bold text-xl">
            🏠 Retounen Akèy
        </a>
        {% endif %}
    </div>
</body>
</html>"""

FORGOT_PASSWORD_HTML = """<!DOCTYPE html>
<html lang="ht">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bliye Modpas - Quiz Foot</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { 
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); 
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
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
</head>
<body class="text-gray-100">
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
</body>
</html>"""

# ----------------- DECORATOR SEKIRITE -----------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'uid' not in session:
            print(f"⚠️ Aksè refize: {request.path}")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Rate limiting pou pwoteksyon kont atak brute force
from collections import defaultdict
from time import time

# Sistèm rate limiting senp (an memwa)
login_attempts = defaultdict(list)
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_TIME = 300  # 5 minit

def check_rate_limit(identifier):
    """Tcheke si yon IP oswa email gen twòp tantativ"""
    now = time()
    # Netwaye tantativ ki pi vye ke LOCKOUT_TIME
    login_attempts[identifier] = [t for t in login_attempts[identifier] if now - t < LOCKOUT_TIME]
    
    if len(login_attempts[identifier]) >= MAX_LOGIN_ATTEMPTS:
        return False
    
    login_attempts[identifier].append(now)
    return True

# Middleware pou sekirite headers
@app.after_request
def add_security_headers(response):
    """Ajoute headers sekirite a chak repons"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    # Content Security Policy
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://www.gstatic.com https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com; "
        "img-src 'self' data: https:; "
        "font-src 'self' data: https://fonts.gstatic.com; "
        "connect-src 'self' https://*.firebaseapp.com https://*.googleapis.com;"
    )
    return response

# ----------------- ROUTES -----------------

@app.route('/')
def index():
    logged_in = 'uid' in session
    return render_template_string(INDEX_HTML, logged_in=logged_in)

@app.route('/login')
def login():
    if 'uid' in session:
        return redirect(url_for('dashboard'))
    return render_template_string(LOGIN_HTML)

@app.route('/signup')
def signup():
    if 'uid' in session:
        return redirect(url_for('dashboard'))
    return render_template_string(SIGNUP_HTML)

@app.route('/forgot_password')
def forgot_password():
    if 'uid' in session:
        return redirect(url_for('dashboard'))
    return render_template_string(FORGOT_PASSWORD_HTML)

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
        # Validasyon rate limit
        client_ip = request.remote_addr
        if not check_rate_limit(f"verify_{client_ip}"):
            return jsonify({'success': False, 'error': 'Twòp tantativ. Eseye pita.'}), 429

        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Done manke'}), 400
            
        id_token = data.get('idToken')
        
        if not id_token:
            return jsonify({'success': False, 'error': 'Token manke'}), 400

        # Validasyon token Firebase
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']
        email = decoded_token.get('email', '')
        
        # Validasyon email
        if not email or '@' not in email:
            return jsonify({'success': False, 'error': 'Imèl pa valid'}), 400
        
        print(f"✅ Token verifye: {email}")

        user_ref = db.collection('users').document(uid)
        user_doc = user_ref.get()

        if not user_doc.exists:
            username = decoded_token.get('name', email.split('@')[0])
            # Sanitize username
            username = username[:50]  # Limit length
            
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

        # Kreye sesyon sekirize
        session.permanent = True
        session['uid'] = uid
        session['email'] = email
        session['username'] = user_data.get('username', email.split('@')[0])[:50]
        session['last_activity'] = datetime.now().isoformat()
        
        return jsonify({'success': True, 'uid': uid})

    except auth.InvalidIdTokenError:
        print(f"❌ Token pa valid")
        session.clear()
        return jsonify({'success': False, 'error': 'Token pa valid'}), 401
    except Exception as e:
        print(f"❌ Erè Verifikasyon Token: {str(e)}")
        session.clear()
        return jsonify({'success': False, 'error': 'Erè sèvè'}), 500

@app.route('/api/create_user', methods=['POST'])
def create_user_doc():
    try:
        # Rate limit validation
        client_ip = request.remote_addr
        if not check_rate_limit(f"create_{client_ip}"):
            return jsonify({'success': False, 'error': 'Twòp tantativ. Eseye pita.'}), 429

        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Done manke'}), 400
            
        uid = data.get('uid')
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()

        # Validasyon done
        if not uid or not username or not email:
            return jsonify({'success': False, 'error': 'Done manke pou kreyasyon itilizatè'}), 400

        # Validasyon email format
        if '@' not in email or len(email) < 5:
            return jsonify({'success': False, 'error': 'Imèl pa valid'}), 400

        # Validasyon username (3-50 karaktè, sèlman alfanimerik)
        if len(username) < 3 or len(username) > 50:
            return jsonify({'success': False, 'error': 'Non itilizatè dwe genyen 3-50 karaktè'}), 400

        # Sanitize username - retire karaktè espesyal
        import re
        username = re.sub(r'[^a-zA-Z0-9_\s-]', '', username)

        user_data = {
            'uid': uid,
            'email': email.lower(),
            'username': username,
            'subscription_status': 'free',
            'quiz_score': 0,
            'purchased_ppv': [],
            'created_at': firestore.SERVER_TIMESTAMP,
            'last_login': firestore.SERVER_TIMESTAMP
        }
        
        db.collection('users').document(uid).set(user_data)
        print(f"✅ Dokiman itilizatè kreye: {email}")
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"❌ Erè kreyasyon dokiman Firestore: {str(e)}")
        return jsonify({'success': False, 'error': 'Erè sèvè'}), 500

@app.route('/dashboard')
@login_required
def dashboard():
    uid = session.get('uid')
    
    # Tcheke aktivite sesyon (timeout apre 24h inaktivite)
    last_activity = session.get('last_activity')
    if last_activity:
        last_time = datetime.fromisoformat(last_activity)
        if datetime.now() - last_time > timedelta(hours=24):
            session.clear()
            return redirect(url_for('login'))
    
    # Mete ajou last_activity
    session['last_activity'] = datetime.now().isoformat()
    
    try:
        user_doc = db.collection('users').document(uid).get()
        
        if not user_doc.exists:
            session.clear()
            return redirect(url_for('login'))
            
        user_data = user_doc.to_dict()
        
        user = {
            'username': user_data.get('username', 'Itilizatè')[:50],
            'subscription_status': user_data.get('subscription_status', 'free'),
            'quiz_score': min(max(user_data.get('quiz_score', 0), 0), 100),  # Limit 0-100
            'purchased_ppv': user_data.get('purchased_ppv', []),
        }
        
        return render_template_string(DASHBOARD_HTML, user=user)

    except Exception as e:
        print(f"❌ Erè nan dashboard: {str(e)}")
        session.clear()
        return redirect(url_for('login'))

@app.route('/subscription')
@login_required
def subscription():
    return render_template_string(SUBSCRIPTION_HTML)

@app.route('/match_stream/<match_id>')
@login_required
def match_stream(match_id):
    # Validasyon match_id
    if not match_id.isdigit() or match_id not in MATCH_DATABASE:
        return redirect(url_for('dashboard'))

    match_info = MATCH_DATABASE[match_id]
    uid = session.get('uid')

    try:
        user_doc = db.collection('users').document(uid).get()
        
        if not user_doc.exists:
            session.clear()
            return redirect(url_for('login'))
            
        user_data = user_doc.to_dict()
        subscription_status = user_data.get('subscription_status', 'free')

        has_access = subscription_status == 'active'

        # Tcheke PPV si pa Premium
        if not has_access and match_info.get('is_ppv'):
            purchased_ppv = user_data.get('purchased_ppv', [])
            if match_id in purchased_ppv:
                has_access = True
                
        # Match gratis
        if not match_info.get('is_ppv'):
            has_access = True

        # Anrejistre vizyon match (analytics)
        if has_access:
            db.collection('match_views').add({
                'user_id': uid,
                'match_id': match_id,
                'timestamp': firestore.SERVER_TIMESTAMP
            })

        return render_template_string(MATCH_STREAM_HTML, 
                                      match_name=match_info['name'],
                                      league=match_info['league'],
                                      match_date=match_info['date'],
                                      ppv_price=match_info['ppv_price'],
                                      match_id=match_id,
                                      has_access=has_access)
    except Exception as e:
        print(f"❌ Erè nan match_stream: {str(e)}")
        return redirect(url_for('dashboard'))                  match_id=match_id,
                                  has_access=has_access)

@app.route('/buy_ppv/<match_id>')
@login_required
def show_ppv_purchase(match_id):
    # Validasyon match_id
    if not match_id.isdigit() or match_id not in MATCH_DATABASE:
        return redirect(url_for('dashboard'))
        
    if not MATCH_DATABASE[match_id].get('is_ppv'):
        return redirect(url_for('dashboard'))
    
    match_info = MATCH_DATABASE[match_id]
    
    # Tcheke si itilizatè a deja achte match sa a
    try:
        uid = session.get('uid')
        user_doc = db.collection('users').document(uid).get()
        
        if user_doc.exists:
            purchased_ppv = user_doc.to_dict().get('purchased_ppv', [])
            if match_id in purchased_ppv:
                return redirect(url_for('match_stream', match_id=match_id))
    except Exception as e:
        print(f"⚠️ Erè tcheke achte: {str(e)}")
    
    return render_template_string(BUY_PPV_HTML, 
                                  match_name=match_info['name'],
                                  league=match_info['league'],
                                  match_date=match_info['date'],
                                  ppv_price=match_info['ppv_price'],
                                  match_id=match_id)

@app.route('/process_ppv_purchase/<match_id>', methods=['POST'])
@login_required
def process_ppv_purchase(match_id):
    # Validasyon match_id pou prevni injection
    if not match_id.isdigit() or match_id not in MATCH_DATABASE:
        return redirect(url_for('dashboard'))
    
    if not MATCH_DATABASE[match_id].get('is_ppv'):
        return redirect(url_for('dashboard'))
    
    # Rate limit pou prevni atak
    client_ip = request.remote_addr
    if not check_rate_limit(f"ppv_{client_ip}"):
        return render_template_string(ERROR_PAYMENT_HTML, 
                                      error_message="Twòp tantativ. Tanpri tann kèk minit.",
                                      match_id=match_id)
    
    time.sleep(2)
    
    # Validasyon done fòm
    card_number = request.form.get('card_number', '').strip()
    card_holder = request.form.get('card_holder_name', '').strip()
    expiry = request.form.get('expiry', '').strip()
    cvv = request.form.get('cvv', '').strip()
    
    # Validasyon baz
    if not all([card_number, card_holder, expiry, cvv]):
        return render_template_string(ERROR_PAYMENT_HTML, 
                                      error_message="Tanpri ranpli tout chan yo.",
                                      match_id=match_id)
    
    # Similasyon validasyon kat (pa mete enfòmasyon reyèl kat!)
    if '1111' in card_number or len(card_number) < 10:
         return render_template_string(ERROR_PAYMENT_HTML, 
                                       error_message="Nimewo kat la pa valid.",
                                       match_id=match_id)

    try:
        uid = session['uid']
        user_ref = db.collection('users').document(uid)
        
        user_doc = user_ref.get()
        if not user_doc.exists:
            session.clear()
            return redirect(url_for('login'))
            
        purchased_ppv = user_doc.to_dict().get('purchased_ppv', [])
        
        # Tcheke si deja achte
        if match_id in purchased_ppv:
            return render_template_string(SUCCESS_PAYMENT_HTML, 
                                          message=f"Ou gen deja aksè a match sa a!",
                                          match_id=match_id)
        
        # Anrejistre achte a
        user_ref.update({
            'purchased_ppv': firestore.ArrayUnion([match_id]),
            'last_purchase': firestore.SERVER_TIMESTAMP
        })
        
        # Anrejistre transaksyon
        db.collection('transactions').add({
            'user_id': uid,
            'type': 'ppv',
            'match_id': match_id,
            'amount': MATCH_DATABASE[match_id]['ppv_price'],
            'timestamp': firestore.SERVER_TIMESTAMP,
            'status': 'completed'
        })
        
        print(f"✅ PPV Match {match_id} achte pou {session['email']}")
        
        return render_template_string(SUCCESS_PAYMENT_HTML, 
                                      message=f"Ou achte aksè a {MATCH_DATABASE[match_id]['name']} pou ${MATCH_DATABASE[match_id]['ppv_price']}!",
                                      match_id=match_id)
    
    except Exception as e:
        print(f"❌ Erè pandan achte PPV: {str(e)}")
        return render_template_string(ERROR_PAYMENT_HTML, 
                                      error_message="Erè sèvè. Tanpri eseye ankò.",
                                      match_id=match_id)

@app.route('/process_payment', methods=['POST'])
@login_required
def process_payment():
    plan = request.form.get('plan', '').strip()
    
    if plan != 'monthly_premium':
        return redirect(url_for('subscription'))

    # Rate limit
    client_ip = request.remote_addr
    if not check_rate_limit(f"sub_{client_ip}"):
        return render_template_string(ERROR_PAYMENT_HTML, 
                                      error_message="Twòp tantativ. Tanpri tann kèk minit.",
                                      match_id=None)

    time.sleep(2)
    
    try:
        uid = session['uid']
        user_ref = db.collection('users').document(uid)
        
        # Verifye itilizatè a egziste
        user_doc = user_ref.get()
        if not user_doc.exists:
            session.clear()
            return redirect(url_for('login'))
        
        # Tcheke si deja aktif
        current_status = user_doc.to_dict().get('subscription_status')
        if current_status == 'active':
            return render_template_string(SUCCESS_PAYMENT_HTML, 
                                          message="Abònman ou deja aktif!",
                                          match_id=None)
        
        # Aktive abònman
        subscription_end = datetime.now() + timedelta(days=30)
        user_ref.update({
            'subscription_status': 'active',
            'subscription_start': firestore.SERVER_TIMESTAMP,
            'subscription_end': subscription_end,
            'last_payment': firestore.SERVER_TIMESTAMP
        })
        
        # Anrejistre transaksyon
        db.collection('transactions').add({
            'user_id': uid,
            'type': 'subscription',
            'plan': 'monthly_premium',
            'amount': 9.99,
            'timestamp': firestore.SERVER_TIMESTAMP,
            'status': 'completed'
        })
        
        print(f"✅ Abònman Premium aktive pou {session['email']}")
        
        return render_template_string(SUCCESS_PAYMENT_HTML, 
                                      message="Abònman Premium ou aktive! Jwi tout match yo!",
                                      match_id=None)
    
    except Exception as e:
        print(f"❌ Erè pandan abònman Premium: {str(e)}")
        return render_template_string(ERROR_PAYMENT_HTML, 
                                      error_message="Erè sèvè. Tanpri eseye ankò.",
                                      match_id=None)


if __name__ == '__main__':
    app.run(debug=True, port=5000)