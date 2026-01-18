import requests
import json
from datetime import datetime

# Configuration
TUTOR_BASE_URL = "https://tutor-docker-sti.onrender.com"
OUTPUT_FILE = f"discovery_tutor_routes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    END = '\033[0m'

def print_color(message, color=None, end='\n'):
    if color:
        print(f"{color}{message}{Colors.END}", end=end)
    else:
        print(message, end=end)

def test_endpoint(base_url, endpoint, method="GET", data=None):
    """Test un endpoint et retourne le résultat"""
    url = f"{base_url}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data if data else {}, timeout=10)
        else:
            response = requests.request(method, url, timeout=10)
        
        return {
            "status": response.status_code,
            "success": response.status_code < 400,
            "response": response.text[:200] if response.text else "Empty",
            "time": response.elapsed.total_seconds()
        }
    except Exception as e:
        return {
            "status": "ERROR",
            "success": False,
            "response": str(e)[:200],
            "time": 0
        }

def discover_routes():
    """Découvre les routes disponibles"""
    
    print_color("\n" + "="*100, Colors.CYAN)
    print_color("DÉCOUVERTE DES ROUTES API TUTEUR", Colors.CYAN)
    print_color("="*100, Colors.CYAN)
    print_color(f"\n📍 URL de base: {TUTOR_BASE_URL}", Colors.BLUE)
    print_color(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", Colors.BLUE)
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        
        def log(message):
            f.write(message + '\n')
            f.flush()
        
        log("="*100)
        log(f"DÉCOUVERTE DES ROUTES API TUTEUR - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        log("="*100)
        log(f"\nURL de base: {TUTOR_BASE_URL}\n")
        
        # Liste des endpoints à tester
        endpoints_to_test = [
            # Racine
            ("GET", "/", "Racine de l'API"),
            ("GET", "/docs", "Documentation Swagger"),
            ("GET", "/openapi.json", "OpenAPI spec"),
            
            # API v1
            ("GET", "/api/v1", "Base API v1"),
            ("GET", "/api/v1/docs", "Docs API v1"),
            ("GET", "/api/v1/openapi.json", "OpenAPI v1"),
            
            # Routes selon la doc fournie
            ("POST", "/api/v1/decide", "Decide endpoint"),
            ("POST", "/api/v1/session/start", "Start session"),
            ("POST", "/api/v1/hint", "Request hint"),
            ("POST", "/api/v1/answer", "Submit answer"),
            ("POST", "/api/v1/case/end", "End case"),
            ("POST", "/api/v1/case/next", "Get next case"),
            ("GET", "/api/v1/session/1/1038", "Get session info"),
            ("GET", "/api/v1/sessions/learner/1", "Get learner sessions"),
            
            # Autres variations possibles
            ("GET", "/health", "Health check"),
            ("GET", "/api/health", "API Health check"),
            ("GET", "/api/v1/health", "API v1 Health"),
            ("GET", "/tutor", "Tutor endpoint"),
            ("GET", "/api/tutor", "API Tutor"),
            ("GET", "/api/v1/tutor", "API v1 Tutor"),
        ]
        
        print_color("\n🔍 Test des endpoints...\n", Colors.YELLOW)
        log("\n" + "─"*100)
        log("RÉSULTATS DES TESTS")
        log("─"*100 + "\n")
        
        available = []
        not_found = []
        errors = []
        
        for method, endpoint, description in endpoints_to_test:
            print_color(f"Testing {method:6} {endpoint:40} ", Colors.BLUE, end='')
            
            result = test_endpoint(TUTOR_BASE_URL, endpoint, method)
            
            log(f"\n{method} {endpoint}")
            log(f"Description: {description}")
            log(f"Status: {result['status']}")
            log(f"Response: {result['response']}")
            log(f"Time: {result['time']:.2f}s")
            
            if result['success']:
                print_color("✅ DISPONIBLE", Colors.GREEN)
                available.append((method, endpoint, description, result['status']))
            elif result['status'] == 404:
                print_color("❌ 404 Not Found", Colors.RED)
                not_found.append((method, endpoint, description))
            elif result['status'] == 405:
                print_color("⚠️  405 Method Not Allowed", Colors.YELLOW)
                not_found.append((method, endpoint, description))
            else:
                print_color(f"⚠️  {result['status']}", Colors.YELLOW)
                errors.append((method, endpoint, description, result['status']))
        
        # Résumé
        print_color("\n" + "="*100, Colors.CYAN)
        print_color("RÉSUMÉ DE LA DÉCOUVERTE", Colors.CYAN)
        print_color("="*100, Colors.CYAN)
        
        log("\n" + "="*100)
        log("RÉSUMÉ")
        log("="*100)
        
        summary = f"""
📊 Statistiques:
   • Endpoints testés: {len(endpoints_to_test)}
   • Disponibles: {len(available)}
   • Non trouvés (404): {len(not_found)}
   • Erreurs: {len(errors)}
"""
        print_color(summary, Colors.BLUE)
        log(summary)
        
        if available:
            print_color("\n✅ ENDPOINTS DISPONIBLES:", Colors.GREEN)
            log("\n✅ ENDPOINTS DISPONIBLES:")
            for method, endpoint, desc, status in available:
                msg = f"   {method:6} {endpoint:40} → {status} - {desc}"
                print_color(msg, Colors.GREEN)
                log(msg)
        
        if errors:
            print_color("\n⚠️  ENDPOINTS AVEC ERREURS:", Colors.YELLOW)
            log("\n⚠️  ENDPOINTS AVEC ERREURS:")
            for method, endpoint, desc, status in errors:
                msg = f"   {method:6} {endpoint:40} → {status} - {desc}"
                print_color(msg, Colors.YELLOW)
                log(msg)
        
        # Tester la racine pour voir s'il y a un message
        print_color("\n🔍 Test détaillé de la racine:", Colors.CYAN)
        log("\n🔍 Test détaillé de la racine:")
        
        try:
            response = requests.get(TUTOR_BASE_URL, timeout=10)
            print_color(f"\nStatus: {response.status_code}", Colors.BLUE)
            print_color(f"Response:", Colors.BLUE)
            print_color(response.text[:500], Colors.YELLOW)
            
            log(f"\nRacine ({TUTOR_BASE_URL}):")
            log(f"Status: {response.status_code}")
            log(f"Headers: {dict(response.headers)}")
            log(f"Response:\n{response.text}")
        except Exception as e:
            print_color(f"Erreur: {str(e)}", Colors.RED)
            log(f"Erreur: {str(e)}")
        
        # Recommandations
        print_color("\n💡 RECOMMANDATIONS:", Colors.CYAN)
        log("\n💡 RECOMMANDATIONS:")
        
        recommendations = """
1. Si /docs ou /openapi.json est disponible, consultez la documentation Swagger
2. Vérifiez que l'API Tuteur est bien déployée sur Render
3. Les routes peuvent avoir un préfixe différent (ex: /tutor/api/v1/...)
4. L'API peut nécessiter une authentification (API Key, JWT)
5. Contactez l'équipe de développement pour confirmer les routes exactes
"""
        print_color(recommendations, Colors.YELLOW)
        log(recommendations)
        
        log("\n" + "="*100)
        log(f"Rapport complet sauvegardé dans: {OUTPUT_FILE}")
        log(f"Date fin: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        log("="*100)
    
    print_color(f"\n📄 Rapport complet: {OUTPUT_FILE}", Colors.GREEN)
    print_color("="*100 + "\n", Colors.CYAN)

if __name__ == "__main__":
    try:
        discover_routes()
    except KeyboardInterrupt:
        print_color("\n\n⚠️  Découverte interrompue", Colors.YELLOW)
    except Exception as e:
        print_color(f"\n\n❌ ERREUR: {str(e)}", Colors.RED)
        import traceback
        traceback.print_exc()