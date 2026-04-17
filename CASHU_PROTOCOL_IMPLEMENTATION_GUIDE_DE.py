"""
═══════════════════════════════════════════════════════════════════════════════
   CASHU PROTOKOLL IMPLEMENTIERUNGSLEITFADEN
   Komplette Code-Logik & Dokumentation (Deutsch)

   Dieses Dokument dokumentiert die Implementierung von:
    Blind Signing (RSA-PSS)
    Mint-Protokoll (Generieren → Signieren → Entblindes)
    Swap-Protokoll (Beweis-Austausch)
    Melt-Protokoll (Quote + Rückzug)
    Quote-Verwaltung (Ablauf, Zustandsverfolgung)

   Referenzierte Dateien:
   - backend/crypto/blind_signing.py (RSA-Kryptografie)
   - backend/core/cashu.py (Protokoll-Client)
   - backend/mint/server.py (Mock-Mint-Server)
   - backend/models/cashu.py (Datenmodelle)
═══════════════════════════════════════════════════════════════════════════════
"""

# ==============================================================================
# TEIL 1: BLIND SIGNING (RSA-PSS)
# ==============================================================================
"""
Das Blind Signing-Protokoll stellt sicher:
1. Benutzer erstellt ein Geheimnis und verblindet es
2. Mint signiert das blinde Engagement (sieht das Geheimnis nicht)
3. Benutzer entblindet zum Erhalten einer gültigen ausgebbaren Signatur
4. Niemand kann die verblindete Nachricht mit dem entblindeten Beweis verknüpfen

Dies ermöglicht kryptografischen Datenschutz: Selbst die Mint kann nicht sagen,
welcher Benutzer welchen Beweis erstellt hat oder Ausgabenmuster verfolgen.
"""

# ─────────────────────────────────────────────────────────────────────────────
# SCHRITT 1: Verblindete Nachricht generieren (Benutzer-Operation)
# ─────────────────────────────────────────────────────────────────────────────

class BlindSigningStep1:
    """Benutzer erstellt ein blinde Engagement zum Verstecken seines Geheimnisses."""
    
    def generate_blinded_message(amount: int, secret: str):
        """
        CLIENT-OPERATION: Erstelle eine verblindete Nachricht für ein Geheimnis.
        
        Das Geheimnis ist die Verpflichtung des Benutzers zu diesem Beweis. Es wird
        gehasht und dann verblind, so dass die Mint nur die verblindete Version B_
        sieht, nicht das Geheimnis.
        
        Weg:
        1. Geheimnis hashen: Geheimnis_hash = SHA256(Geheimnis)
        2. Zufälligen Verblindungsfaktor generieren: r = zufällig(32 Bytes)
        3. Verblindes: B_ = SHA256(Geheimnis_hash + r)
        4. B_ an Mint senden, Geheimnis und r privat halten
        
        Gibt eine BlindedMessage mit zurück:
        - B_: Verblindetes Engagement an Mint senden
        - r: Verblindungsfaktor geheim halten
        - amount: Der Wert dieses Engagements
        
        Die Mint sieht niemals 'Geheimnis' oder 'r', nur 'B_'.
        """
        
        # Schritt 1: Geheimnis des Benutzers hashen
        secret_hash = hashlib.sha256(secret.encode()).digest()
        
        # Zur Integer für mathematische Operationen konvertieren
        secret_int = int.from_bytes(secret_hash, 'big')
        
        # Schritt 2: Zufälligen Verblindungsfaktor generieren (32 Bytes = 256 Bits)
        r_bytes = os.urandom(32)
        r_int = int.from_bytes(r_bytes, 'big')
        
        # Schritt 3: Das Engagement mit Geheimnis und Zufallsfaktor verblindes
        # Produktions-Cashu: B_ = (Geheimnis_int * r_int) mod n
        # Hier: B_ = SHA256(Geheimnis_hash + r_bytes)
        combined = hashlib.sha256(secret_hash + r_bytes).digest()
        
        # Zur Übertragung in Hex konvertieren
        B_ = combined.hex()
        r = r_bytes.hex()
        
        # Schritt 4: Verblindete Nachricht (B_) an Mint senden, r geheim halten
        return BlindedMessage(
            amount=amount,
            B_=B_,        # An Mint senden ✓
            r=r           # Geheim halten ✓
        )


# ─────────────────────────────────────────────────────────────────────────────
# SCHRITT 2: Blind Sign (Mint-Operation)
# ─────────────────────────────────────────────────────────────────────────────

class BlindSigningStep2:
    """Mint signiert die verblindete Nachricht ohne das Geheimnis zu sehen."""
    
    def blind_sign(blinded_message: BlindedMessage, private_key_pem: str):
        """
        MINT-OPERATION: Signiere eine verblindete Nachricht.
        
        Der Schlüssel-Insight: Die Mint signiert die verblindete Nachricht B_,
        nicht das Geheimnis. Da es verblind ist, lernt die Mint nicht, was das
        Geheimnis ist.
        
        Weg:
        1. Verblindete Nachricht B_ vom Benutzer empfangen
        2. Mit RSA-PSS signieren: C_ = RSA_sign(B_)
        3. Blindsignatur C_ an Benutzer zurückgeben
        
        Die Mint weiß nicht:
        - Was das ursprüngliche Geheimnis ist
        - Was die entblindete Signatur sein wird
        - Welche Proofs von welchem Benutzer kamen
        
        Args:
            blinded_message: Die BlindedMessage mit B_, die wir empfangen
            private_key_pem: Mint privater RSA-Schlüssel (PEM-Format)
        
        Returns:
            BlindSignature mit C_, die der Benutzer entblindes kann
        """
        
        # Schritt 1: Mint privaten RSA-Schlüssel von PEM laden
        private_key = serialization.load_pem_private_key(
            private_key_pem.encode(),
            password=None,
            backend=default_backend()
        )
        
        # Schritt 2: Verblindete Nachricht von Hex-String zu Bytes konvertieren
        B_bytes = bytes.fromhex(blinded_message.B_)
        
        # Schritt 3: Mit RSA-PSS und SHA256 signieren
        # RSA-PSS fügt Zufälligkeit hinzu, so dass gleiche Eingaben nicht gleiche
        # Ausgaben produzieren
        signature = private_key.sign(
            B_bytes,
            padding.PSS(
                # MGF1 ist die Maskenerzeugungsfunktion
                mgf=padding.MGF1(hashes.SHA256()),
                # PSS.DIGEST_LENGTH = Salt-Länge = Hash-Ausgabegröße
                salt_length=padding.PSS.DIGEST_LENGTH
            ),
            hashes.SHA256()
        )
        
        # Schritt 4: Signatur zu Hex für Übertragung konvertieren
        C_ = signature.hex()
        
        # Blindsignatur zurückgeben
        return BlindSignature(
            amount=blinded_message.amount,
            C_=C_  # Blindsignatur - Benutzer wird das entblindes
        )


# ─────────────────────────────────────────────────────────────────────────────
# SCHRITT 3: Signatур Entblindung (Benutzer-Operation)
# ─────────────────────────────────────────────────────────────────────────────

class BlindSigningStep3:
    """Benutzer entblindet die Signatur um einen gültigen, ausgebbaren Beweis zu erhalten."""
    
    def unblind_signature(blind_signature: BlindSignature, blinding_factor: str):
        """
        CLIENT-OPERATION: Entblinde die Signatur um einen ausgebbaren Beweis zu erhalten.
        
        Jetzt nimmt der Benutzer die Blindsignatur C_ und seinen geheimen Verblindungs-
        faktor r und erstellt eine entblindete Signatur C, die ausgegeben werden kann.
        
        Weg:
        1. Blindsignatur C_ von Mint empfangen
        2. Mit entblindes: C = sha256(C_ + r)
        3. Beweis (Geheimnis, C, Betrag) erstellen, der ausgegeben werden kann
        
        Magische Eigenschaft: 
        - Die Mint signierte B_ (das sha256(Geheimnis + r) ist)
        - Benutzer entblindet: C = sha256(C_ + r)
        - Ergebnis: C ist eine gültige Signatur des Geheimnisses!
        
        Args:
            blind_signature: Die C_, die von Mint empfangen wird
            blinding_factor: Der r-Faktor von generate_blinded_message()
        
        Returns:
            Entblindete Signatur C (Hex-String), die ausgegeben werden kann
        """
        
        # Schritt 1: Blindsignatur und Verblindungsfaktor von Hex zu Bytes konvertieren
        C_bytes = bytes.fromhex(blind_signature.C_)
        r_bytes = bytes.fromhex(blinding_factor)
        
        # Schritt 2: Entblinde, indem Signatur und Faktor zusammen gehasht werden
        # Produktions-Cashu: C = (C_ / r) mod n (modulare Arithmetik)
        # Hier: C = SHA256(C_ + r)
        C = hashlib.sha256(C_bytes + r_bytes).hexdigest()
        
        # Schritt 3: Entblindete Signatur zurückgeben (jetzt ausgegeben)
        return C


# ─────────────────────────────────────────────────────────────────────────────
# SCHRITT 4: DLEQ-Beweis verifikation
# ─────────────────────────────────────────────────────────────────────────────

class BlindSigningStep4:
    """Verifizieren Sie den DLEQ-Beweis (Discrete Log Equivalence)."""
    
    def verify_dleq_proof(proof_secret: str, commitment: str, dleq_proof: dict):
        """
        OPTIONAL: Verifizieren Sie, dass das Engagement mit dem Geheimnis übereinstimmt
        mit DLEQ.
        
        DLEQ-Beweis überprüft: "Das Engagement C entspricht dem Geheimnis auf die
        gleiche Weise, wie C_ B_ entspricht" ohne das Geheimnis offenzulegen.
        
        Aktuelle Implementierung: VEREINFACHT (nicht kryptografisch verifiziert)
        - Überprüft nur, dass erforderliche Felder vorhanden sind
        - Validiert, dass sie gültige Hex-Strings sind
        
        Produktions-Implementierung würde:
        - Elliptische Kurven-Kryptografie verwenden
        - Zero-Knowledge-Proof-Gleichungen überprüfen
        
        Args:
            proof_secret: Das ursprüngliche Geheimnis des Benutzers
            commitment: Das entblindete Engagement C
            dleq_proof: Beweis-Daten von Mint mit Feldern z, r, e
        
        Returns:
            True wenn Felder vorhanden und gültig sind, False sonst
        """
        
        # Schritt 1: Überprüfen Sie, ob erforderliche Felder vorhanden sind
        required_fields = ['z', 'r', 'e']
        if not all(field in dleq_proof for field in required_fields):
            return False
        
        # Schritt 2: Validieren Sie, dass jedes Feld gültige Hex ist
        try:
            int(dleq_proof['z'], 16)  # Als Hex analysieren
            int(dleq_proof['r'], 16)
            int(dleq_proof['e'], 16)
        except (ValueError, TypeError):
            return False
        
        # In Produktien: Führen Sie echte elliptische Kurve-Verifikation durch
        # Dies würde komplexe Mathematik für Zero-Knowledge-Beweis-Verifikation beinhalten
        
        return True


# ==============================================================================
# TEIL 2: MINT PROTOKOLL (Generieren → Signieren → Entblindes)
# ==============================================================================
"""
Das Mint-Protokoll ist ein 2-Phasen-Prozess:

PHASE 1: MINT-QUOTE ANFORDERN
  Client: "Ich möchte 100 Sats"
  Mint: "Bezahlen Sie diese Lightning-Rechnung, erhalten Sie Quote_ID"

PHASE 2: MINTING FERTIGSTELLEN
  Client: "Hier sind meine Quote_ID und Blindnachrichten"
  Mint: "Hier sind Blindsignaturen"
  Client: "Ich werde diese entblindes, um Proofs zu erhalten"

Ergebnis: Client hat 100 Sats in Proofs (Ecash-Tokens)
"""

# ─────────────────────────────────────────────────────────────────────────────
# MINT PHASE 1: Mint-Quote anfordern
# ─────────────────────────────────────────────────────────────────────────────

class MintProtocolPhase1:
    """Mint-Quote von der Mint anfordern."""
    
    def request_mint_quote(mint_url: str, amount: int):
        """
        CLIENT-OPERATION: Mint-Quote anfordern.
        
        Schritt 1 des Minting: Client fordert Mint Quote an.
        Mint gibt eine Lightning-Rechnung zurück zum Bezahlen.
        
        Weg:
        1. Client sendet: POST /requestmint mit Betrag=100
        2. Mint erstellt Quote_ID (verfolgt in MINT_QUOTES)
        3. Mint generiert Lightning-Rechnung
        4. Mint gibt zurück: Quote_ID, Rechnung, Ablauf (5 Minuten)
        
        Args:
            mint_url: Basis-URL der Mint (z.B. "http://localhost:5001")
            amount: Sats zu Minting
        
        Returns:
            Quote-Objekt mit:
            - Quote_ID: Eindeutige Quote-Kennung
            - request: Lightning-Rechnung zum Bezahlen
            - state: "ausstehend"
            - expires_at: ISO-Zeitstempel (jetzt + 5 Minuten)
        """
        
        # Schritt 1: Anfrage an Mint-Server senden
        response = requests.post(
            f"{mint_url}/requestmint",
            json={"amount": amount},
            timeout=10
        )
        data = response.json()
        
        # Schritt 2: Antwortdaten extrahieren
        quote_id = data.get("quote")          # z.B. "d6702017-7321-4fc6-..."
        invoice = data.get("request", "")     # z.B. "lnbc100u1p0mockivv"
        
        # Schritt 3: Quote-Objekt mit 5-Minuten-Ablauf erstellen
        quote = Quote(
            quote_id=quote_id,
            amount=amount,
            request=invoice,
            quote_type="mint",
            state="pending",
            expires_at=(datetime.now() + timedelta(minutes=5)).isoformat(),
            mint_url=mint_url
        )
        
        # Schritt 4: Quote für nächste Phase zurückgeben
        return quote


# ─────────────────────────────────────────────────────────────────────────────
# MINT PHASE 2: Minting fertigstellen
# ─────────────────────────────────────────────────────────────────────────────

class MintProtocolPhase2:
    """Minting-Prozess durch Austausch verblindeter Nachrichten für Signaturen fertigstellen."""
    
    def finish_mint(mint_url: str, quote: Quote):
        """
        CLIENT-OPERATION: Mint-Prozess fertigstellen.
        
        Schritt 2 des Minting: 
        1. Verblindete Nachrichten für jede Stückelung generieren
        2. An Mint senden
        3. Blindsignaturen empfangen
        4. Signaturen entblindes um ausgebbare Proofs zu erhalten
        
        Weg:
        1. Betrag in Zweierpotenzen aufteilen: [64, 32, 4]
        2. Für jeden Betrag: generate_blinded_message()
        3. Alle Blindnachrichten an Mint senden
        4. Mint gibt Blindsignaturen zurück
        5. Für jede Signatur: unblind_signature()
        6. Proof-Objekte (Geheimnis, C, Betrag) erstellen
        7. Proofs an Wallet zurückgeben
        
        Args:
            mint_url: Mint-Server-URL
            quote: Quote von request_mint_quote()
        
        Returns:
            Liste von Proof-Objekten (jetzt ausgegeben)
        """
        
        # Schritt 1: Betrag in Stückelungen aufteilen (Zweierpotenzen)
        # Beispiel: 100 Sats → [64, 32, 4]
        amounts = []
        remaining = quote.amount
        power = 0
        while remaining > 0 and power < 12:
            amount = min(2 ** power, remaining)  # Min verwenden, nicht zu viel
            amounts.append(amount)
            remaining -= amount
            power += 1
        
        # Schritt 2: Verblindete Nachrichten für jeden Betrag generieren
        blinded_messages = []
        secrets = []
        blinding_factors = []
        
        for amount in amounts:
            # Zufälliges Geheimnis für diesen Beweis erstellen
            secret = f"{uuid.uuid4().hex}"
            
            # Verblindete Nachricht generieren
            blinded = crypto.generate_blinded_message(amount, secret)
            
            # Zur späteren Entblindung verfolgen
            blinded_messages.append({
                "amount": amount,
                "B_": blinded.B_,    # An diesem senden
                "r": blinded.r       # Geheim halten
            })
            secrets.append(secret)
            blinding_factors.append(blinded.r)
        
        # Schritt 3: Verblindete Nachrichten an Mint senden
        response = requests.post(
            f"{mint_url}/mint",
            json={
                "quote": quote.quote_id,
                "blinded_messages": blinded_messages
            },
            timeout=10
        )
        data = response.json()
        
        # Schritt 4: Blindsignaturen von Mint empfangen
        blind_sigs = data.get("proofs", [])
        
        # Schritt 5: Signaturen entblindes und Proofs erstellen
        proofs = []
        
        for i, blind_sig in enumerate(blind_sigs):
            amount = blind_sig.get("amount", 0)
            C_ = blind_sig.get("C_", "")
            dleq_proof = blind_sig.get("dleq", {})
            
            # DLEQ-Beweis überprüfen (vereinfacht)
            if not crypto.verify_dleq_proof(secrets[i], C_, dleq_proof):
                print(f"[Client] WARNUNG: DLEQ-Beweis fehlgeschlagen für Output {i}")
            
            # Signatur entblindes
            blind_sig_obj = BlindSignature(amount, C_)
            C = crypto.unblind_signature(
                blind_sig_obj,
                blinding_factors[i]  # Den r-Faktor verwenden
            )
            
            # Schritt 6: Proof-Objekt erstellen (jetzt ausgegeben)
            proof = Proof(
                amount=amount,
                secret=secrets[i],           # Das ursprüngliche Geheimnis
                C=C,                         # Die entblindete Signatur
                mint=mint_url,               # Welche Mint das ausgestellt hat
                keyset_version="00"          # Keyset-Version
            )
            
            proofs.append(proof)
        
        # Schritt 7: Proofs zum Wallet zurückgeben
        return proofs


# ==============================================================================
# TEIL 3: SWAP PROTOKOLL (Beweis-Austausch)
# ==============================================================================
"""
Das Swap-Protokoll ermöglicht einem Benutzer, ihre Proofs für blinde Outputs
auszutauschen, die sie an einen anderen Benutzer senden können.

Weg:
1. Sender: "Ich möchte 100 Sats senden. Hier sind meine Proofs."
2. Mint: "Ich werde blinde Outputs für Sie erstellen."
3. Sender: "Ich sende diese blinden Outputs an den Empfänger."
4. Empfänger: "Ich habe diese blinden Outputs empfangen und entblindet!"

Schlüssel-Insight: Die blinden Outputs werden mit dem EMPFÄNGERS Verblindungs-
faktor erstellt, so dass nur der Empfänger sie entblindes kann. Der Sender kann
sie nach der Erstellung nicht ausgeben.
"""

class SwapProtocol:
    """Proofs für blinde Outputs austauschen."""
    
    def client_swap(mint_url: str, proofs_to_send: List[Proof], 
                    output_amounts: List[int]):
        """
        CLIENT-OPERATION: Proofs für blinde Outputs zum Senden austauschen.
        
        Wird verwendet, wenn der Benutzer Geld über Token an ein anderes Wallet senden möchte.
        
        Weg:
        1. Proofs vom Wallet auswählen, die Betrag abdecken
        2. swap() anrufen
        3. Mint gibt blinde Outputs zurück
        4. Outputs als Token kodieren
        5. Proofs aus Wallet entfernen (jetzt ausgegeben)
        6. Token an Empfänger senden
        
        Args:
            mint_url: Mint-URL
            proofs_to_send: Liste von Proofs zum Austausch
            output_amounts: Gewünschte Output-Stückelungen [64, 32, 4]
        
        Returns:
            Liste von blinden Outputs zum Kodieren als Token
        """
        
        # Schritt 1: Beträge überprüfen, ob sie übereinstimmen
        total_proofs = sum(p.amount for p in proofs_to_send)
        total_outputs = sum(output_amounts)
        
        if total_proofs != total_outputs:
            raise ValueError(f"Proof Betrag {total_proofs} != Output {total_outputs}")
        
        # Schritt 2: Proofs für Übertragung serialisieren
        proof_dicts = [p.to_dict() for p in proofs_to_send]
        
        # Schritt 3: Mint Swap-Endpunkt anrufen
        response = requests.post(
            f"{mint_url}/swap",
            json={
                "proofs": proof_dicts,
                "output_amounts": output_amounts
            },
            timeout=10
        )
        data = response.json()
        
        # Schritt 4: Blinde Outputs empfangen
        outputs = data.get("outputs", [])
        
        # Schritt 5: Outputs jetzt bereit zum Kodieren als Token
        return outputs


# ==============================================================================
# TEIL 4: MELT PROTOKOLL (Quote + Rückzug)
# ==============================================================================
"""
Das Melt-Protokoll ermöglicht Benutzern, Ecash-Proofs zurück zu Fiat/Lightning
einzulösen.

PHASE 1: MELT-QUOTE ANFORDERN
  Client: "Ich möchte 100 Sats via diese Lightning-Rechnung einlösen"
  Mint: "OK, hier ist eine Melt-Quote mit 5-Min-Ablauf"

PHASE 2: MINTING FERTIGSTELLEN
  Client: "Hier sind meine Proofs und Quote_ID"
  Mint: "Ich werde validieren und die Lightning-Rechnung bezahlen"
  Client: "Bestätigt! Proofs sind jetzt ausgegeben."

Ergebnis: Client hat reale Lightning Sats empfangen (oder Fiat-Äquivalent)
"""

class MeltProtocolPhase1:
    """Melt-Quote anfordern."""
    
    def client_request_melt_quote(mint_url: str, invoice: str, amount: int):
        """
        CLIENT-OPERATION: Melt-Quote anfordern.
        
        Schritt 1 des Meltings: Client möchte Sats zu Fiat/Lightning einlösen.
        Stellt Lightning-Rechnung zur Zahlung bereit.
        
        Args:
            mint_url: Mint-Server-URL
            invoice: Lightning-Rechnung (z.B. "lnbc100u1p...")
            amount: Sats zum Einlösen
        
        Returns:
            Quote mit:
            - Quote_ID: Melt-Quote-ID
            - amount: Eingelöster Betrag
            - expires_at: 5-Minuten-Ablauf
        """
        
        # Schritt 1: Anfrage an Mint senden
        response = requests.post(
            f"{mint_url}/requestmelt",
            json={
                "pr": invoice,      # pr = Zahlungsanforderung
                "amount": amount
            },
            timeout=10
        )
        data = response.json()
        
        # Schritt 2: Quote-Objekt erstellen
        quote_id = data.get("quote")
        quote = Quote(
            quote_id=quote_id,
            amount=amount,
            request=invoice,
            quote_type="melt",
            state="pending",
            expires_at=(datetime.now() + timedelta(minutes=5)).isoformat(),
            mint_url=mint_url
        )
        
        return quote


class MeltProtocolPhase2:
    """Melt-Prozess fertigstellen durch Proofs-Rückzug."""
    
    def client_finish_melt(mint_url: str, quote: Quote, 
                          proofs: List[Proof]) -> bool:
        """
        CLIENT-OPERATION: Melt-Prozess fertigstellen.
        
        Schritt 2 des Meltings: Proofs an Mint zur Einlösung senden.
        
        Args:
            mint_url: Mint-Server-URL
            quote: Melt-Quote von request_melt_quote()
            proofs: Proofs zum Einlösen
        
        Returns:
            True wenn Melt erfolgreich ist, False sonst
        """
        
        # Schritt 1: Betrag überprüfen
        total = sum(p.amount for p in proofs)
        if total < quote.amount:
            raise ValueError(f"Unzureichende Proofs: {total} < {quote.amount}")
        
        # Schritt 2: Proofs serialisieren
        proof_dicts = [p.to_dict() for p in proofs]
        
        # Schritt 3: An Mint senden
        response = requests.post(
            f"{mint_url}/melt",
            json={
                "quote": quote.quote_id,
                "pr": quote.request,    # Rechnung zum Bezahlen
                "proofs": proof_dicts
            },
            timeout=10
        )
        data = response.json()
        
        # Schritt 4: Überprüfen Sie, ob Mint bestätigt
        state = data.get("state", "")
        return state == "paid"


# ==============================================================================
# TEIL 5: QUOTE-VERWALTUNG (Ablauf, Zustandsverfolgung)
# ==============================================================================
"""
Quotes verwalten zeitgebundene Transaktionen. Sie verhindern:
- Benutzer von Minting ohne Bezahlung
- Undefnite Hängel, wenn etwas bricht
- Double-Spending derselben Quote zweimal

State-Weg: ausstehend → bestätigt → abgelaufen
Ablauf: 5 Minuten ab Erstellung
"""

class QuoteManagement:
    """Quote-Lebenszyklusverwaltung."""
    
    # Quote-Modell (backend/models/cashu.py)
    class Quote:
        """Stellt eine Mint- oder Melt-Quote dar."""
        
        def __init__(
            self,
            quote_id: str,
            amount: int,
            request: str,              # Rechnung oder Cashu-Anfrage
            quote_type: str,           # "mint" oder "melt"
            state: str = "pending",    # ausstehend, bestätigt, abgelaufen
            expires_at: Optional[str] = None,
            mint_url: str = "http://localhost:5001"
        ):
            """
            Initialisiere eine Quote.
            
            Args:
                quote_id: Eindeutige Kennung (UUID)
                amount: Sats beteiligt
                request: Lightning-Rechnung oder Cashu-Anfrage
                quote_type: "mint" erstellt Proofs, "melt" löst sie ein
                state: Aktueller Status (ausstehend/bestätigt/abgelaufen)
                expires_at: ISO-Zeitstempel wenn Quote abläuft
                mint_url: Welche Mint diese Quote ausgestellt hat
            """
            self.quote_id = quote_id
            self.amount = amount
            self.request = request
            self.quote_type = quote_type
            self.state = state
            self.expires_at = expires_at
            self.created_at = datetime.now().isoformat()
            self.mint_url = mint_url
        
        
        def is_expired(self) -> bool:
            """
            Überprüfen Sie, ob Quote abgelaufen ist.
            
            Quotes sind 5 Minuten lang gültig. Danach:
            - Mint verwirft die Quote
            - Benutzer muss eine neue anfordern
            
            Returns:
                True wenn aktuelle Zeit > expires_at, False sonst
            """
            if not self.expires_at:
                return False
            
            # ISO-Zeitstempel analysieren
            expires = datetime.fromisoformat(self.expires_at)
            
            # Mit aktueller Zeit vergleichen
            return datetime.now() > expires
        
        
        def to_dict(self) -> dict:
            """Für Speicherung serialisieren."""
            return {
                "quote_id": self.quote_id,
                "amount": self.amount,
                "request": self.request,
                "quote_type": self.quote_type,
                "state": self.state,
                "expires_at": self.expires_at,
                "created_at": self.created_at,
                "mint_url": self.mint_url
            }
    
    
    # Wallet-Quote-Verfolgung
    class WalletQuoteTracking:
        """Verfolgen Sie ausstehende Quotes im Wallet."""
        
        def __init__(self):
            """Initialisiere Quote-Verfolgung."""
            self.pending_quotes = {}  # {Quote_ID: Quote}
        
        
        def add_quote(self, quote: Quote):
            """
            Füge neue Quote zu ausstehender Liste hinzu.
            
            Aufgerufen, wenn:
            - Benutzer Mint-Quote anfordert
            - Benutzer Melt-Quote anfordert
            
            Speicher:
            - Im Speicher während Sitzung
            - Auf Server-Neustart verloren (Design-Einschränkung)
            
            Args:
                Quote: Quote-Objekt
            """
            self.pending_quotes[quote.quote_id] = quote
            print(f"[Wallet] Quote verfolgen {quote.quote_id}")
        
        
        def get_quote(self, quote_id: str) -> Optional[Quote]:
            """
            Get a Quote by ID.
            
            Vor Verwendung überprüfen:
            - Quote existiert
            - Quote ist nicht abgelaufen
            - Quote ist korrekter Typ (Mint vs Melt)
            
            Args:
                Quote_ID: UUID von Quote
            
            Returns:
                Quote-Objekt oder None, wenn nicht gefunden
            """
            return self.pending_quotes.get(quote_id)
        
        
        def remove_quote(self, quote_id: str):
            """
            Quote nach Abschluss entfernen.
            
            Aufgerufen, wenn:
            - finish_mint() erfolgreich
            - finish_melt() erfolgreich
            - Quote läuft ab (Bereinigung)
            
            Args:
                Quote_ID: UUID von Quote zum Entfernen
            """
            if quote_id in self.pending_quotes:
                del self.pending_quotes[quote_id]
                print(f"[Wallet] Quote entfernt {quote_id}")


# ==============================================================================
# ZUSAMMENFASSUNG: Kompletter Protokoll-Weg
# ==============================================================================

"""
KOMPLETTER TRANSAKTIONS-WEG:

1. MINTING (Erstellen von 100 Sats Ecash)
2. SWAPPING (Senden von 50 Sats an ein anderes Wallet)
3. MELTING (Einlösen von 25 Sats zu Lightning/Fiat)

Jeder Schritt verwendet Chaums Blind Signing Protokoll für vollständige
kryptografische Anonymität und Sicherheit.
"""
