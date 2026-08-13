"""
K.IA - Moteur de synthese vocale

Deux fournisseurs :
  - "elevenlabs" : appel API ElevenLabs (streaming), retourne du MP3
  - "browser"    : ne fait rien cote serveur, le frontend utilise
                   l'API Web Speech (speechSynthesis)

En cas d'echec ElevenLabs : log d'avertissement + retour None,
le frontend bascule automatiquement sur la voix du navigateur.
"""

import asyncio
import re

import aiohttp

ELEVENLABS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
ELEVENLABS_MODEL = "eleven_multilingual_v2"
ELEVENLABS_FORMAT = "mp3_44100_128"

# Fin de phrase : ponctuation forte suivie d'un espace ou de la fin du texte.
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?…:;])\s+|(?<=\n)")


class TTSEngine:
    """Synthese vocale phrase par phrase, pensee pour le streaming."""

    def __init__(self, provider: str = "elevenlabs", api_key: str = None, voice_id: str = None):
        self.provider = (provider or "browser").lower().strip()
        self.api_key = api_key or ""
        self.voice_id = voice_id or ""
        self.mime_type = "audio/mpeg"

        if self.provider == "elevenlabs" and not (self.api_key and self.voice_id):
            print("[TTS] ELEVENLABS_API_KEY ou ELEVENLABS_VOICE_ID manquant -> bascule sur 'browser'")
            self.provider = "browser"

        print(f"[TTS] Fournisseur : {self.provider.upper()}")

    @property
    def enabled(self) -> bool:
        """True si le serveur produit lui-meme l'audio."""
        return self.provider == "elevenlabs"

    # ------------------------------------------------------------------
    # Decoupage
    # ------------------------------------------------------------------

    def chunk_text(self, text: str, max_chars: int = 150) -> list:
        """
        Decoupe le texte en morceaux prononcables (phrases regroupees),
        chacun d'au plus max_chars caracteres.
        """
        text = (text or "").strip()
        if not text:
            return []

        pieces = [p.strip() for p in _SENTENCE_SPLIT.split(text) if p and p.strip()]

        chunks = []
        buf = ""
        for piece in pieces:
            # Une phrase seule trop longue : on la coupe sur les virgules/espaces.
            while len(piece) > max_chars:
                comma = piece.rfind(",", 0, max_chars)
                if comma >= max_chars // 2:
                    cut = comma + 1          # la virgule reste avec le debut
                else:
                    cut = piece.rfind(" ", 0, max_chars)
                    if cut <= 0:
                        cut = max_chars
                head, piece = piece[:cut].strip(), piece[cut:].strip()
                if buf:
                    chunks.append(buf)
                    buf = ""
                if head:
                    chunks.append(head)

            if not piece:
                continue
            if not buf:
                buf = piece
            elif len(buf) + 1 + len(piece) <= max_chars:
                buf = f"{buf} {piece}"
            else:
                chunks.append(buf)
                buf = piece

        if buf:
            chunks.append(buf)
        return chunks

    # ------------------------------------------------------------------
    # Synthese
    # ------------------------------------------------------------------

    async def synthesize(self, text: str):
        """
        Retourne les octets audio (MP3) ou None.
        None signifie : au frontend de parler (mode 'browser' ou echec API).
        """
        text = (text or "").strip()
        if not text or self.provider != "elevenlabs":
            return None

        url = ELEVENLABS_URL.format(voice_id=self.voice_id)
        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        }
        payload = {
            "text": text,
            "model_id": ELEVENLABS_MODEL,
            "voice_settings": {
                "stability": 0.45,
                "similarity_boost": 0.75,
                "style": 0.0,
                "use_speaker_boost": True,
            },
        }
        params = {"output_format": ELEVENLABS_FORMAT}

        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, headers=headers, json=payload, params=params) as resp:
                    if resp.status != 200:
                        body = (await resp.text())[:300]
                        print(f"[TTS][WARN] ElevenLabs {resp.status}: {body}")
                        return None
                    audio = bytearray()
                    async for block in resp.content.iter_chunked(8192):
                        audio.extend(block)
                    return bytes(audio) if audio else None

        except asyncio.TimeoutError:
            print("[TTS][WARN] ElevenLabs : timeout -> fallback navigateur")
            return None
        except Exception as e:
            print(f"[TTS][WARN] ElevenLabs indisponible ({e}) -> fallback navigateur")
            return None
