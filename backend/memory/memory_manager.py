"""
K.IA - Gestionnaire de memoire

Deux niveaux, volontairement simples :

  memory/
    topics.md              <- memoire long terme (faits sur l'utilisateur)
    sessions/
      2026-08-13_14-30-05.jsonl   <- un fichier JSONL par session

- Court terme : les N derniers tours, relus depuis les fichiers JSONL.
- Long terme  : topics.md, reecrit par le LLM a la fin de chaque session.

Le contexte est injecte dans le system prompt entre les balises
[MEMOIRE] ... [FIN MEMOIRE].
"""

import json
import os
from datetime import datetime

MEMORY_BLOCK_START = "[MÉMOIRE]"
MEMORY_BLOCK_END = "[FIN MÉMOIRE]"

# Garde-fou : on ne laisse pas topics.md grossir indefiniment.
MAX_TOPICS_CHARS = 6000

CONSOLIDATION_PROMPT = """Extrais les informations importantes sur l'utilisateur \
a partir de la conversation ci-dessous, puis fusionne-les avec la memoire existante.

Retiens uniquement ce qui reste utile dans les prochaines conversations :
- identite, role, contexte de vie ou de travail
- preferences explicites (gouts, style de reponse attendu, outils utilises)
- projets en cours, objectifs, contraintes
- faits durables enonces par l'utilisateur

Ignore : les banalites, les questions ponctuelles, la meteo, ce qui est deja obsolete.

Regles de sortie :
- Reponds UNIQUEMENT avec le contenu Markdown complet du nouveau fichier memoire.
- Une puce par fait, formulee a la troisieme personne ("L'utilisateur ...").
- Regroupe les puces sous des titres `## Theme`.
- Fusionne les doublons, mets a jour les faits qui ont change, supprime les faits contredits.
- Pas de preambule, pas de commentaire, pas de bloc de code.
- Si rien d'important n'est a retenir, renvoie la memoire existante telle quelle.

### MEMOIRE EXISTANTE
{topics}

### CONVERSATION A ANALYSER
{transcript}
"""


class MemoryManager:
    """Memoire persistante de K.IA (court terme JSONL + long terme Markdown)."""

    def __init__(self, memory_dir: str, kia_client=None):
        self.memory_dir = os.path.abspath(memory_dir)
        self.sessions_dir = os.path.join(self.memory_dir, "sessions")
        self.topics_path = os.path.join(self.memory_dir, "topics.md")
        self.kia_client = kia_client

        os.makedirs(self.sessions_dir, exist_ok=True)

        self.session_id, self.session_path = self._new_session()

        self.topics = self._load_topics()
        print(
            f"[MEMOIRE] Session {self.session_id} | "
            f"{self.count_memories()} souvenir(s) charge(s) depuis topics.md"
        )

    # ------------------------------------------------------------------
    # Identite de session
    # ------------------------------------------------------------------

    def get_session_id(self) -> str:
        """Identifiant de la session courante, format YYYY-MM-DD_HH-MM-SS."""
        return self.session_id

    def _new_session(self) -> tuple:
        """Retourne (session_id, chemin) en evitant d'ecraser une session existante."""
        base = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        session_id, n = base, 1
        while os.path.exists(os.path.join(self.sessions_dir, f"{session_id}.jsonl")):
            n += 1
            session_id = f"{base}-{n}"
        return session_id, os.path.join(self.sessions_dir, f"{session_id}.jsonl")

    def start_new_session(self) -> str:
        """Ouvre un nouveau fichier de session (appele apres une consolidation)."""
        self.session_id, self.session_path = self._new_session()
        return self.session_id

    # ------------------------------------------------------------------
    # Long terme : topics.md
    # ------------------------------------------------------------------

    def _load_topics(self) -> str:
        try:
            with open(self.topics_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except FileNotFoundError:
            return ""
        except OSError as e:
            print(f"[MEMOIRE][ERREUR] Lecture topics.md : {e}")
            return ""

    def _save_topics(self, content: str):
        content = content.strip()[:MAX_TOPICS_CHARS]
        try:
            with open(self.topics_path, "w", encoding="utf-8") as f:
                f.write(content + "\n")
            self.topics = content
        except OSError as e:
            print(f"[MEMOIRE][ERREUR] Ecriture topics.md : {e}")

    def count_memories(self) -> int:
        """Nombre de faits memorises (une puce = un souvenir)."""
        return sum(
            1
            for line in self.topics.splitlines()
            if line.strip().startswith(("- ", "* "))
        )

    def stats(self) -> dict:
        """Resume de l'etat de la memoire (pour le HUD)."""
        return {
            "session_id": self.session_id,
            "memories": self.count_memories(),
            "turns": len(self._read_session(self.session_path)),
            "sessions": len(self._session_files()),
        }

    # ------------------------------------------------------------------
    # Court terme : sessions/*.jsonl
    # ------------------------------------------------------------------

    def save_turn(self, role: str, content: str):
        """Ajoute un tour au fichier JSONL de la session courante."""
        if not content:
            return
        entry = {
            "role": role,
            "content": content,
            "ts": datetime.now().isoformat(timespec="seconds"),
        }
        try:
            with open(self.session_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError as e:
            print(f"[MEMOIRE][ERREUR] Ecriture session : {e}")

    def _session_files(self) -> list:
        """Fichiers de session tries du plus ancien au plus recent."""
        try:
            names = [n for n in os.listdir(self.sessions_dir) if n.endswith(".jsonl")]
        except OSError:
            return []
        return [os.path.join(self.sessions_dir, n) for n in sorted(names)]

    @staticmethod
    def _read_session(path: str) -> list:
        turns = []
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        turns.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        except FileNotFoundError:
            return []
        except OSError as e:
            print(f"[MEMOIRE][ERREUR] Lecture session : {e}")
        return turns

    def _recent_turns(self, n_last: int) -> list:
        """Les N derniers tours, en remontant sur les sessions precedentes si besoin."""
        turns = []
        for path in reversed(self._session_files()):
            turns = self._read_session(path) + turns
            if len(turns) >= n_last:
                break
        return turns[-n_last:] if n_last > 0 else []

    # ------------------------------------------------------------------
    # Lecture du contexte
    # ------------------------------------------------------------------

    def load_context(self, n_last: int = 10) -> str:
        """Bloc memoire a injecter dans le system prompt."""
        sections = []

        if self.topics:
            sections.append("Ce que tu sais deja sur l'utilisateur :\n" + self.topics)

        turns = self._recent_turns(n_last)
        if turns:
            lines = []
            for t in turns:
                who = "Utilisateur" if t.get("role") == "user" else "K.IA"
                text = (t.get("content") or "").strip().replace("\n", " ")
                if len(text) > 400:
                    text = text[:400] + "..."
                lines.append(f"{who}: {text}")
            sections.append("Derniers echanges :\n" + "\n".join(lines))

        if not sections:
            return ""

        return f"{MEMORY_BLOCK_START}\n" + "\n\n".join(sections) + f"\n{MEMORY_BLOCK_END}"

    # ------------------------------------------------------------------
    # Consolidation (fin de session)
    # ------------------------------------------------------------------

    async def consolidate(self, kia_client=None) -> dict:
        """
        Demande au LLM d'extraire les faits importants de la session courante
        et de les fusionner dans topics.md. Retourne un petit rapport.
        """
        client = kia_client or self.kia_client
        turns = self._read_session(self.session_path)

        if not turns:
            return {"ok": False, "reason": "session vide", "memories": self.count_memories()}

        if client is None:
            return {"ok": False, "reason": "aucun client LLM", "memories": self.count_memories()}

        transcript = "\n".join(
            f"{'Utilisateur' if t.get('role') == 'user' else 'K.IA'}: {(t.get('content') or '').strip()}"
            for t in turns
        )

        prompt = CONSOLIDATION_PROMPT.format(
            topics=self.topics or "(memoire vide)",
            transcript=transcript[:20000],
        )

        try:
            merged = await client.complete(
                system="Tu es le module de memoire de K.IA. Tu produis des fiches "
                       "memoire factuelles et concises, sans commentaire.",
                user=prompt,
                max_tokens=2048,
            )
        except Exception as e:
            print(f"[MEMOIRE][ERREUR] Consolidation : {e}")
            return {"ok": False, "reason": str(e), "memories": self.count_memories()}

        merged = (merged or "").strip()
        if not merged:
            return {"ok": False, "reason": "reponse vide", "memories": self.count_memories()}

        before = self.count_memories()
        self._save_topics(merged)
        after = self.count_memories()
        print(f"[MEMOIRE] Consolidation OK : {before} -> {after} souvenir(s)")

        return {
            "ok": True,
            "session_id": self.session_id,
            "turns": len(turns),
            "memories": after,
            "added": after - before,
        }
