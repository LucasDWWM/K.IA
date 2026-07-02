"""
K.IA - Diagnostic API Claude
Lance ce script seul (sans app.py) pour tester la connexion a Claude directement.

    python diagnostic.py
"""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

async def test_claude():
    print("=== Diagnostic K.IA ===\n")

    # 1. Verification cle API
    if not ANTHROPIC_API_KEY:
        print("[ERREUR] ANTHROPIC_API_KEY introuvable dans le .env !")
        print("  -> Cree un fichier .env avec : ANTHROPIC_API_KEY=sk-ant-...")
        return
    print(f"[OK] Cle API trouvee : {ANTHROPIC_API_KEY[:20]}...")

    # 2. Import Anthropic
    try:
        from anthropic import AsyncAnthropic
        print("[OK] Package 'anthropic' importe")
    except ImportError:
        print("[ERREUR] Package 'anthropic' absent -> pip install anthropic")
        return

    # 3. Appel streaming simple
    client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    print("\n[TEST] Appel streaming a Claude...\n")

    try:
        full_text = ""
        async with client.messages.stream(
            model="claude-sonnet-4-6",
            max_tokens=200,
            system="Tu es K.IA, un assistant vocal francophone. Reponds en 1-2 phrases courtes.",
            messages=[{"role": "user", "content": "Bonjour, presente-toi !"}],
        ) as stream:
            async for event in stream:
                if hasattr(event, "text"):
                    print(event.text, end="", flush=True)
                    full_text += event.text

        print("\n\n[OK] Streaming fonctionne ! Longueur reponse :", len(full_text), "caracteres")

    except Exception as e:
        print(f"\n[ERREUR API] {type(e).__name__}: {e}")
        print("\nCauses possibles :")
        print("  - Cle API incorrecte ou expiree")
        print("  - Pas d'acces au modele claude-sonnet-4-6")
        print("  - Pas de connexion internet")

asyncio.run(test_claude())