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

# ----------------- HTML TEMPLATES -----------------

INDEX_HTML = """<!DOCTYPE html>
<html lang="ht">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Quiz Foot - Akèy</title>
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
    <title>Login - Quiz Foot</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); min-height: 100vh; }
    </style>
</head>
<body class="flex items-center justify-center min-h-screen">
    <div class="bg-gray-800 p-8 rounded-xl shadow-2xl max-w-md w-full">
        <h2 class="text-3xl font-bold text-white text-center mb-6">🔐 Konekte</h2>
        <div id="error-message" class="hidden bg-red-900 text-red-200 p-3 rounded mb-4"></div>
        <form id="login-form">
            <input type="email" id="email" placeholder="Email" required 
                class="w-full p-3 mb-4 bg-gray-700 text-white rounded border-2 border-gray-600 focus:border-blue-500">
            <input type="password" id="password" placeholder="Modpas" required 
                class="w-full p-3 mb-4 bg-gray-700 text-white rounded border-2 border-gray-600 focus:border-blue-500">
            <button type="submit" class="w-full bg-orange-500 hover:bg-orange-600 text-white py-3 rounded font-bold">
                Konekte
            </button>
        </form>
        <p class="text-center mt-4 text-gray-300">
            Pa gen kont? <a href="/signup" class="text-blue-400 hover:underline">Enskri</a>
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

        document.getElementById('login-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const errorDiv = document.getElementById('error-message');
            errorDiv.classList.add('hidden');
            
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
                errorDiv.textContent = '❌ ' + (error.message || 'Erè pandan koneksyon');
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
    <title>Signup - Quiz Foot</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); min-height: 100vh; }
    </style>
</head>
<body class="flex items-center justify-center min-h-screen">
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
            <button type="submit" class="w-full bg-green-500 hover:bg-green-600 text-white py-3 rounded font-bold">
                Enskri Kounye a
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

        document.getElementById('signup-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const errorDiv = document.getElementById('error-message');
            errorDiv.classList.add('hidden');
            
            try {
                const username = document.getElementById('username').value.trim();
                const email = document.getElementById('email').value.trim();
                const password = document.getElementById('password').value;
                
                const userCredential = await createUserWithEmailAndPassword(auth, email, password);
                await updateProfile(userCredential.user, { displayName: username });
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
                let msg = 'Erè pandan enskripsyon';
                if (error.code === 'auth/email-already-in-use') msg = 'Imèl sa a deja anrejistre';
                else if (error.code === 'auth/weak-password') msg = 'Modpas la twò fèb';
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
            <a href="/subscription" class="text-gray-200 hover:text-white">Abònman</a>
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
    <title>Abònman - Quiz Foot</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%); min-height: 100vh; }
    </style>
</head>
<body class="text-gray-100">
    <header class="bg-gray-800 px-6 py-4 flex justify-between items-center">
        <div class="text-2xl font-bold text-orange-500">⚽ QUIZ FOOT</div>
        <nav class="flex gap-4">
            <a href="/" class="text-gray-200 hover:text-white">Akèy</a>
            <a href="/dashboard" class="text-gray-200 hover:text-white">Dashboard</a>
            <a href="/logout" class="bg-red-600 px-4 py-2 rounded-lg">Dekonekte</a>
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
                <form action="{{ url_for('process_payment') }}" method="POST">
                    <input type="hidden" name="plan" value="monthly_premium">
                    <button type="submit" class="w-full bg-orange-500 hover:bg-orange-600 py-3 rounded-lg font-bold text-white">
                        Kòmanse Abònman an
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
</body>
</html>"""

BUY_PPV_HTML = """<!DOCTYPE html>
<html lang="ht">
<head>
    <meta charset="UTF-8">
    <title>Achte PPV - {{ match_name }}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { background: linear-gradient(135deg, #121212 0%, #1a1a2e 100%); min-height: 100vh; }
    </style>
</head>
<body class="text-gray-100">
    <header class="bg-gray-800 px-6 py-4 flex justify-between items-center">
        <div class="text-2xl font-bold text-orange-500">⚽ QUIZ FOOT</div>
        <nav class="flex gap-4">
            <a href="/" class="text-gray-200">Akèy</a>
            <a href="/dashboard" class="text-gray-200">Dashboard</a>
            <a href="/logout" class="bg-red-600 px-4 py-2 rounded-lg">Dekonekte</a>
        </nav>
    </header>
    
    <main class="container mx-auto px-4 py-12">
        <div class="max-w-2xl mx-auto bg-gray-800 p-8 rounded-xl border-t-4 border-orange-500">
            <h2 class="text-3xl font-bold text-center mb-6">Achte Aksè Match PPV</h2>
            <h3 class="text-2xl text-blue-400 text-center mb-2">{{ match_name }}</h3>
            <p class="text-gray-400 text-center mb-6">{{ league }} | {{ match_date }}</p>
            <p class="text-5xl font-bold text-green-400 text-center mb-8">Pri Total: ${{ ppv_price }}</p>
            
            <form action="{{ url_for('process_ppv_purchase', match_id=match_id) }}" method="POST">
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
                
                <button type="submit" class="w-full bg-orange-500 hover:bg-orange-600 text-white py-4 rounded-lg font-bold text-lg">
                    Peye ${{ ppv_price }} epi Jwenn Aksè
                </button>
            </form>
            
            <p class="text-center mt-6">
                <a href="/" class="text-blue-400 hover:underline">Retounen nan Akèy</a>
            </p>
        </div>
    </main>
</body>
</html>"""

MATCH_STREAM_HTML = """<!DOCTYPE html>
<html lang="ht">
<head>
    <meta charset="UTF-8">
    <title>{{ match_name }} - Quiz Foot</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%); min-height: 100vh; }
        .video-container { aspect-ratio: 16/9; background: #000; }
    </style>
</head>
<body class="text-gray-100">
    <header class="bg-gray-800 px-6 py-4 flex justify-between items-center">
        <div class="text-2xl font-bold text-orange-500">⚽ QUIZ FOOT</div>
        <nav class="flex gap-4">
            <a href="/" class="text-gray-200">Akèy</a>
            <a href="/dashboard" class="text-gray-200">Dashboard</a>
            <a href="/logout" class="bg-red-600 px-4 py-2 rounded-lg">Dekonekte</a>
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
</body>
</html>"""

SUCCESS_PAYMENT_HTML = """<!DOCTYPE html>
<html lang="ht">
<head>
    <meta charset="UTF-8">
    <title>Siksè Peman - Quiz Foot</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); min-height: 100vh; }
        @keyframes checkmark {
            0% { transform: scale(0); }
            50% { transform: scale(1.2); }
            100% { transform: scale(1); }
        }
        .check-animated { animation: checkmark 0.6s ease-out; }
    </style>
</head>
<body class="text-gray-100 flex items-center justify-center min-h-screen">
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
</body>
</html>"""

ERROR_PAYMENT_HTML = """<!DOCTYPE html>
<html lang="ht">
<head>
    <meta charset="UTF-8">
    <title>Echèk Peman - Quiz Foot</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { background: linear-gradient(135deg, #1e1e2d 0%, #1a1a2e 100%); min-height: 100vh; }
        @keyframes shake {
            0%, 100% { transform: translateX(0); }
            25% { transform: translateX(-10px); }
            75% { transform: translateX(10px); }
        }
        .shake-animated { animation: shake 0.6s ease-out; }
    </style>
</head>
<body class="text-gray-100 flex items-center justify-center min-h-screen">
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
</body>
</html>"""

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
    username = session.get('username', None)
    print(f"📍 Paj Akèy - Konekte: {logged_in}")
    return render_template_string(INDEX_HTML, logged_in=logged_in, username=username)

@app.route('/login')
def login():
    if 'uid' in session:
        return redirect(url_for('dashboard'))
    print("📍 Paj Login")
    return render_template_string(LOGIN_HTML)

@app.route('/signup')
def signup():
    if 'uid' in session:
        return redirect(url_for('dashboard'))
    print("📍 Paj Signup")
    return render_template_string(SIGNUP_HTML)

@app.route('/logout')
def logout():
    username = session.get('username', 'Itilizatè')
    session.clear()
    print(f"👋 {username} dekonekte")
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
        
        user_ref = db.collection('users').document(uid)
        user_data = user_ref.get()
        
        if not user_data.exists:
            new_user = {
                'username': decoded_token.get('name', email.split('@')[0]),
                'email': email,
                'subscription': False,
                'quiz_score': 0,
                'uid': uid,
                'created_at': firestore.SERVER_TIMESTAMP
            }
            user_ref.set(new_user)
            print(f"✅ Nouvo itilizatè: {email}")
        
        user_info = user_ref.get().to_dict()
        session['uid'] = uid
        session['email'] = email
        session['username'] = user_info.get('username', 'Itilizatè')
        session.permanent = True
        
        return jsonify({'success': True, 'uid': uid, 'username': session['username']}), 200
        
    except Exception as e:
        print(f"❌ Erè verify_token: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/dashboard')
@login_required
def dashboard():
    user_uid = session['uid']
    try:
        user_ref = db.collection('users').document(user_uid).get()
        user_info = user_ref.to_dict() or {}
        
        user_data = {
            'username': user_info.get('username', 'Itilizatè'),
            'email': user_info.get('email', ''),
            'subscription_status': 'active' if user_info.get('subscription', False) else 'basic',
            'quiz_score': user_info.get('quiz_score', 0)
        }
        
        print(f"📊 Dashboard: {user_data['username']}")
        return render_template_string(DASHBOARD_HTML, user=user_data)
    except Exception as e:
        print(f"❌ Erè Dashboard: {str(e)}")
        return f"Erè: {str(e)}", 500

@app.route('/subscription')
@login_required
def subscription():
    user_uid = session['uid']
    try:
        user_ref = db.collection('users').document(user_uid).get()
        user_info = user_ref.to_dict() or {}
        
        user_data = {
            'username': user_info.get('username', 'Itilizatè'),
            'subscription_status': 'active' if user_info.get('subscription', False) else 'basic'
        }
        
        print(f"📍 Subscription: {user_data['username']}")
        return render_template_string(SUBSCRIPTION_HTML, user=user_data)
    except Exception as e:
        print(f"❌ Erè Subscription: {str(e)}")
        return f"Erè: {str(e)}", 500

@app.route('/process_payment', methods=['POST'])
@login_required
def process_payment():
    plan = request.form.get('plan', 'monthly_premium')
    print(f"💳 Peman: {session.get('username')}, Plan: {plan}")
    return redirect(url_for('activate_subscription'))

@app.route('/activate_subscription')
@login_required
def activate_subscription():
    user_uid = session['uid']
    try:
        db.collection('users').document(user_uid).update({
            'subscription': True,
            'subscription_date': firestore.SERVER_TIMESTAMP
        })
        print(f"✅ Abònman aktive: {session.get('username')}")
        return render_template_string(SUCCESS_PAYMENT_HTML, 
                                    message="🎉 Abònman ou aktive!",
                                    match_id=None, ppv_price=9.99)
    except Exception as e:
        print(f"❌ Erè aktivasyon: {str(e)}")
        return f"Erè: {str(e)}", 500

@app.route('/buy_ppv/<match_id>')
@login_required
def show_ppv_purchase(match_id):
    match_info = MATCH_DATABASE.get(match_id)
    if not match_info:
        return "Match pa egziste", 404
    
    if not match_info['is_ppv'] or match_info['ppv_price'] <= 0:
        return redirect(url_for('match_stream', match_id=match_id))
    
    print(f"💰 Buy PPV: {match_info['name']}")
    
    user_uid = session['uid']
    ppv_doc_id = f"{user_uid}_{match_id}"
    ppv_ref = db.collection('ppv_purchases').document(ppv_doc_id).get()
    
    if ppv_ref.exists:
        purchase_data = ppv_ref.to_dict()
        exp_date = purchase_data.get('access_expires')
        if exp_date and exp_date > datetime.now():
            return redirect(url_for('match_stream', match_id=match_id))
    
    return render_template_string(BUY_PPV_HTML,
                                match_name=match_info['name'],
                                league=match_info['league'],
                                match_date=match_info['date'],
                                ppv_price=match_info['ppv_price'],
                                match_id=match_id)

@app.route('/process_ppv_purchase/<match_id>', methods=['POST'])
@login_required
def process_ppv_purchase(match_id):
    user_uid = session['uid']
    match_info = MATCH_DATABASE.get(match_id)
    payment_method = request.form.get('payment_method')
    
    if not match_info or not match_info['is_ppv']:
        return render_template_string(ERROR_PAYMENT_HTML,
                                    error_message="Match PPV pa egziste",
                                    match_id=match_id), 404
    
    price = match_info['ppv_price']
    print(f"💳 PPV: {payment_method}, Pri: ${price}")
    time.sleep(1)
    
    try:
        purchase_data = {
            'user_id': user_uid,
            'match_id': match_id,
            'match_name': match_info['name'],
            'price': price,
            'payment_method': payment_method,
            'purchase_date': firestore.SERVER_TIMESTAMP,
            'access_expires': datetime.now() + timedelta(days=2)
        }
        
        doc_id = f"{user_uid}_{match_id}"
        db.collection('ppv_purchases').document(doc_id).set(purchase_data)
        
        print(f"✅ PPV achte: {match_info['name']}")
        return render_template_string(SUCCESS_PAYMENT_HTML,
                                    message=f"🎉 Aksè achte pou {match_info['name']}!",
                                    match_id=match_id, ppv_price=price)
    except Exception as e:
        print(f"❌ Erè PPV: {str(e)}")
        return render_template_string(ERROR_PAYMENT_HTML,
                                    error_message=f"Erè: {str(e)}",
                                    match_id=match_id), 500

@app.route('/match_stream/<match_id>')
@login_required
def match_stream(match_id):
    user_uid = session['uid']
    match_info = MATCH_DATABASE.get(match_id)
    
    if not match_info:
        return "Match pa egziste", 404
    
    try:
        user_ref = db.collection('users').document(user_uid).get()
        user_data = user_ref.to_dict() or {}
        has_subscription = user_data.get('subscription', False)
        
        ppv_doc_id = f"{user_uid}_{match_id}"
        ppv_ref = db.collection('ppv_purchases').document(ppv_doc_id).get()
        
        has_ppv_access = False
        if ppv_ref.exists:
            purchase_data = ppv_ref.to_dict()
            exp_date = purchase_data.get('access_expires')
            if exp_date and isinstance(exp_date, datetime):
                has_ppv_access = exp_date > datetime.now()
            else:
                has_ppv_access = True
        
        requires_payment = match_info['is_ppv'] and match_info['ppv_price'] > 0
        has_access = (not requires_payment) or has_subscription or has_ppv_access
        
        print(f"🎬 Stream: {match_info['name']}, Aksè: {has_access}")
        
        if requires_payment and not has_access:
            return redirect(url_for('show_ppv_purchase', match_id=match_id))
        
        return render_template_string(MATCH_STREAM_HTML,
                                    match_name=match_info['name'],
                                    league=match_info['league'],
                                    match_date=match_info['date'],
                                    has_access=has_access,
                                    match_id=match_id,
                                    ppv_price=match_info['ppv_price'],
                                    is_ppv=match_info['is_ppv'])
    except Exception as e:
        print(f"❌ Erè Stream: {str(e)}")
        return f"Erè: {str(e)}", 500

@app.errorhandler(404)
def page_not_found(e):
    print(f"❌ 404: {request.path}")
    return render_template_string(ERROR_PAYMENT_HTML,
                                error_message="Paj sa a pa egziste",
                                match_id=None), 404

@app.errorhandler(500)
def internal_error(e):
    print(f"❌ 500: {str(e)}")
    return render_template_string(ERROR_PAYMENT_HTML,
                                error_message="Erè entèn",
                                match_id=None), 500

# ----------------- START -----------------
if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("🚀 QUIZ FOOT - Aplikasyon ap kòmanse...")
    print("=" * 60)
    print("📱 http://localhost:5000")
    print("=" * 60 + "\n")
    app.run(debug=True, host='0.0.0.0', port=5000)