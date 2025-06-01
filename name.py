from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import requests
import spacy
import pandas as pd
from difflib import SequenceMatcher
from typing import List, Dict
import re
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# CORS configuration
origins = [
    "http://localhost:3000",
    "http://localhost:8000",
    "http://localhost:8001",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Chargement modèle NLP SpaCy
try:
    nlp = spacy.load('en_core_web_sm')
except OSError:
    import subprocess
    import sys
    subprocess.run([sys.executable, "-m", "spacy", "download", "en_core_web_sm"], check=True)
    nlp = spacy.load('en_core_web_sm')

# Profanity check
PROFANITY_WORDS = ["naco", "fuck", "shit", "merde", "pute", "con", "connard", "asshole", "idiot", "stupid", "bastard","nik","potano","zebi", "nik", "kelb", "sharmuta", "bent", "benti", "bnit", "3ayz", "taban", "haywan", "tiz", "kos", "kosomak", "3irs","زب", "نيك", "كلب", "شرموطة", "بنت", "بنتي", "بنيت", "عيز", "تعبان", "حيوان", "طيز", "كس", "كس أمك", "عرص"]

def contains_profanity(text: str) -> bool:
    text_lower = text.lower()
    for word in PROFANITY_WORDS:
        if re.search(rf"\b{re.escape(word)}\b", text_lower):
            return True
    return False

# Chargement base de données Excel
try:
    df = pd.read_excel(r'C:\Users\DeLL\OneDrive\Desktop\cc.xlsx')
    names_fr = df['NOM_FR'].str.lower().str.strip().tolist()
    names_ar = df['NOM_AR'].str.strip().tolist()
    types = df.get('TYPE', ['SARL'] * len(df)).tolist()
    print("✅ Loaded real company database")
except Exception as e:
    print(f"⚠️ Failed to load companies database: {e}")
    names_fr, names_ar, types = [], [], []

# Historique des conversations
conversation_history: Dict[str, List[Dict[str, str]]] = {}

# Pydantic model
class ChatRequest(BaseModel):
    prompt: str
    style: str = "concise"
    session_id: str = "default"
    short_response: bool = False
    extract_mode: bool = True

def similar(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()

def check_name_reserved(name: str, threshold: float = 0.85) -> bool:
    name_lower = name.lower().strip()
    if name_lower in names_fr or name_lower in [x.lower() for x in names_ar]:
        return True
    for existing_name in names_fr:
        if similar(name_lower, existing_name) >= threshold:
            return True
    for existing_name in names_ar:
        if similar(name_lower, existing_name.lower()) >= threshold:
            return True
    return False

def extract_company_name(text: str) -> str:
    patterns = [
        r"nom [d']?entreprise ['\"]?(.*?)['\"]?",
        r"vérifier (le )?nom (.*?)( pour|$)",
        r"nom: (.*?)(\s|$)",
        r"proposer (le )?nom (.*?)(\s|$)",
        r"['\"]?(.*?)['\"]? (est|serait) (mon|le) nom"
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            for group in reversed(match.groups()):
                if group and len(group.strip()) > 2:
                    return group.strip()
    return text.strip()

def extract_business_concept(text: str) -> str:
    keywords = {
        "technologie": ["tech", "informatique", "logiciel", "ai", "it", "développement", "numérique"],
        "restauration": ["restaurant", "café", "bistro", "cuisine", "food", "repas", "nourriture"],
        "commerce": ["boutique", "shop", "store", "vente", "ecommerce", "marchand", "retail"],
        "construction": ["bâtiment", "construction", "immobilier", "architecte", "ingénierie", "bâtir"],
        "santé": ["médical", "santé", "pharmacie", "clinique", "hôpital", "docteur", "médecin"],
        "éducation": ["école", "éducation", "formation", "université", "apprentissage", "enseignement"],
        "consulting": ["conseil", "consulting", "service", "expert", "stratégie", "conseiller"],
        "agriculture": ["agricole", "ferme", "cultiver", "élevage", "culture", "produits naturels"]
    }
    text_lower = text.lower()
    for sector, terms in keywords.items():
        for term in terms:
            if term in text_lower:
                return sector
    return "général"

def get_suggestions(name: str, concept: str = "général", count: int = 3) -> List[str]:
    base_name = name.strip().lower()
    suggestions = []
    concept_based = {
        "technologie": [f"{base_name} technologies", f"{base_name} solutions", f"{base_name} digital", f"{base_name} labs", f"{base_name} innovations"],
        "restauration": [f"le {base_name}", f"{base_name} cuisine", f"{base_name} gourmet", f"{base_name} bistro", f"{base_name} delice"],
        "commerce": [f"{base_name} shop", f"boutique {base_name}", f"{base_name} store", f"{base_name} market", f"{base_name} outlet"],
        "construction": [f"{base_name} construction", f"{base_name} bâtiment", f"{base_name} travaux", f"{base_name} immobilier", f"{base_name} architecture"],
        "santé": [f"{base_name} santé", f"{base_name} médical", f"{base_name} care", f"{base_name} pharma", f"{base_name} clinique"],
        "éducation": [f"{base_name} éducation", f"{base_name} academy", f"{base_name} learning", f"{base_name} institute", f"{base_name} campus"],
        "consulting": [f"{base_name} consulting", f"{base_name} conseil", f"{base_name} partners", f"{base_name} solutions", f"{base_name} advisory"],
        "agriculture": [f"{base_name} ferme", f"{base_name} agriculture", f"{base_name} nature", f"{base_name} bio", f"ferme {base_name}"],
        "général": [f"{base_name} group", f"{base_name} services", f"{base_name} tunisie", f"{base_name} international", f"{base_name} excellence"]
    }
    for suggestion in concept_based.get(concept, concept_based["général"]):
        if not check_name_reserved(suggestion) and suggestion not in suggestions:
            suggestions.append(suggestion)
            if len(suggestions) >= count:
                break
    generic_suggestions = [f"new {base_name}", f"global {base_name}", f"{base_name} premium", f"{base_name} pro", f"elite {base_name}", f"{base_name} excellence", f"{base_name} vision"]
    for suggestion in generic_suggestions:
        if len(suggestions) < count and not check_name_reserved(suggestion) and suggestion not in suggestions:
            suggestions.append(suggestion)
    return suggestions[:count]

@app.post("/chat")
async def chat(data: ChatRequest):
    prompt = data.prompt
    style = data.style
    session_id = data.session_id
    short_response = data.short_response
    extract_mode = data.extract_mode

    if session_id not in conversation_history:
        conversation_history[session_id] = []
    conversation_history[session_id].append({"role": "user", "content": prompt})

    # Vérifier la présence de gros mots
    if contains_profanity(prompt):
        return {"response": "⚠️ Votre message contient des propos inappropriés. Veuillez reformuler."}

    nom_propose = extract_company_name(prompt) if extract_mode else prompt
    concept = extract_business_concept(prompt) if extract_mode else "général"
    is_reserved = check_name_reserved(nom_propose)

    if is_reserved:
        suggestions = get_suggestions(nom_propose, concept)
        if short_response:
            response = f"❌ '{nom_propose}' est réservé. Suggestions: {', '.join(suggestions)}"
        else:
            response = f"❌ Désolé, le nom '{nom_propose}' est déjà réservé.\nVoici quelques suggestions : {', '.join(suggestions)}"
    else:
        response = f"✅ felicitation ! Le nom '{nom_propose}' est disponible pour votre entreprise."

    conversation_history[session_id].append({"role": "assistant", "content": response})
    return {"response": response}


@app.get("/", response_class=HTMLResponse)
async def interface():
    return """
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>HBA-ASSISTANT</title>
        <style>
            * {
                box-sizing: border-box;
            }
            body {
                margin: 0;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background-color: #202123;
                color: #e5e5e5;
                display: flex;
                flex-direction: column;
                height: 100vh;
                transition: background-color 0.3s, color 0.3s;
            }
            body.light {
                background-color: #f5f5f5;
                color: #202123;
            }
            header {
                background-color: #343541;
                padding: 20px;
                font-size: 1.8rem;
                font-weight: bold;
                text-align: center;
                border-bottom: 1px solid #444;
                color: #fff;
                user-select: none;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 15px;
            }
            body.light header {
                background-color: #e0e0e0;
                color: #202123;
                border-color: #ccc;
            }
            header img {
                height: 40px;
            }
            #chat-container {
                flex: 1;
                overflow-y: auto;
                padding: 20px;
                display: flex;
                flex-direction: column;
                gap: 10px;
                background-color: inherit;
            }
            .message {
                max-width: 70%;
                padding: 14px 18px;
                border-radius: 12px;
                line-height: 1.4;
                white-space: pre-wrap;
                word-break: break-word;
                font-size: 1rem;
                transition: background-color 0.3s, color 0.3s;
            }
            .user {
                align-self: flex-end;
                background: linear-gradient(135deg, #4f46e5, #4338ca);
                color: white;
                border-bottom-right-radius: 0;
            }
            .bot {
                align-self: flex-start;
                background-color: #343541;
                border-bottom-left-radius: 0;
                color: #d1d5db;
                box-shadow: 0 0 8px rgba(0,0,0,0.3);
            }
            body.light .bot {
                background-color: #ddd;
                color: #333;
                box-shadow: none;
            }
            #input-container {
                display: flex;
                padding: 15px 20px;
                background-color: #343541;
                border-top: 1px solid #444;
                gap: 10px;
            }
            body.light #input-container {
                background-color: #e0e0e0;
                border-color: #ccc;
            }
            #prompt {
                flex: 1;
                border: none;
                padding: 12px 15px;
                border-radius: 25px;
                font-size: 1rem;
                outline: none;
                background-color: #202123;
                color: #e5e5e5;
                box-shadow: inset 0 0 5px rgba(255,255,255,0.1);
                transition: background-color 0.3s ease, color 0.3s ease;
            }
            body.light #prompt {
                background-color: #fff;
                color: #202123;
                box-shadow: inset 0 0 5px rgba(0,0,0,0.1);
            }
            #prompt::placeholder {
                color: #6b7280;
            }
            #prompt:focus {
                background-color: #2c2c34;
                box-shadow: inset 0 0 8px rgba(79, 70, 229, 0.6);
            }
            body.light #prompt:focus {
                background-color: #d0d0f5;
                box-shadow: inset 0 0 8px rgba(79, 70, 229, 0.6);
            }
            /* Scrollbar styling */
            #chat-container::-webkit-scrollbar {
                width: 8px;
            }
            #chat-container::-webkit-scrollbar-track {
                background: #1e1e23;
            }
            #chat-container::-webkit-scrollbar-thumb {
                background-color: #4f46e5;
                border-radius: 4px;
            }
            body.light #chat-container::-webkit-scrollbar-track {
                background: #f0f0f0;
            }
            body.light #chat-container::-webkit-scrollbar-thumb {
                background-color: #6366f1;
            }
            /* Responsive */
            @media (max-width: 600px) {
                .message {
                    max-width: 90%;
                    font-size: 0.9rem;
                }
                header {
                    font-size: 1.4rem;
                }
            }
            /* Avatar animation */
            #avatar {
                width: 50px;
                height: 50px;
                background: url('https://i.imgur.com/1Xhp1Xv.gif') no-repeat center center;
                background-size: contain;
                margin-right: 10px;
                user-select: none;
            }
            /* Button styles */
            button, select {
                background-color: #4f46e5;
                border: none;
                color: white;
                padding: 8px 12px;
                border-radius: 6px;
                cursor: pointer;
                font-size: 1rem;
                transition: background-color 0.3s ease;
            }
            button:hover, select:hover {
                background-color: #4338ca;
            }
            #controls {
                display: flex;
                gap: 10px;
                align-items: center;
                margin-left: 20px;
            }
        </style>
    </head>
    <body>
        <header>
            <div id="avatar" title="Avatar animé"></div>
            <img src="https://i.imgur.com/2yaf2wb.png" alt="Logo HBA" title="Logo HBA" />
            HBA-ASSISTANT
            <div id="controls">
                <select id="style-select" title="Choisir la personnalité du bot">
                    <option value="formel" selected>Formel</option>
                    <option value="amical">Amical</option>
                    <option value="concise">Concise</option>
                </select>
                <button id="toggle-theme" title="Basculer thème clair/sombre">🌗</button>
                <button id="record-btn" title="Activer/désactiver la reconnaissance vocale">🎤</button>
                <button id="save-btn" title="Enregistrer la conversation">💾</button>
            </div>
        </header>
        <div id="chat-container"></div>
        <div id="input-container">
            <input id="prompt" type="text" placeholder="Écris un message et appuie sur Entrée..." autocomplete="off" autofocus />
        </div>

        <script>
            const promptInput = document.getElementById("prompt");
            const chatContainer = document.getElementById("chat-container");
            const styleSelect = document.getElementById("style-select");
            const toggleThemeBtn = document.getElementById("toggle-theme");
            const recordBtn = document.getElementById("record-btn");
            const saveBtn = document.getElementById("save-btn");
            const avatar = document.getElementById("avatar");

            // Gestion thème clair/sombre avec stockage local
            function setTheme(theme) {
                if(theme === "light") {
                    document.body.classList.add("light");
                } else {
                    document.body.classList.remove("light");
                }
                localStorage.setItem("theme", theme);
            }
            toggleThemeBtn.addEventListener("click", () => {
                if(document.body.classList.contains("light")) {
                    setTheme("dark");
                } else {
                    setTheme("light");
                }
            });
            const savedTheme = localStorage.getItem("theme") || "dark";
            setTheme(savedTheme);

            // Fonction d'ajout de message
            function addMessage(text, sender) {
                const message = document.createElement("div");
                message.classList.add("message", sender);
                message.textContent = text;
                chatContainer.appendChild(message);
            }
            // Suppression dernier message bot (ex: "réfléchit")
            function removeLastBotMessage() {
                const messages = document.querySelectorAll(".message.bot");
                if (messages.length > 0) {
                    messages[messages.length - 1].remove();
                }
            }
            // Scroll bas
            function scrollToBottom() {
                chatContainer.scrollTop = chatContainer.scrollHeight;
            }

            // Affichage progressif de la réponse
            async function displayProgressive(text, sender="bot") {
                const message = document.createElement("div");
                message.classList.add("message", sender);
                chatContainer.appendChild(message);
                scrollToBottom();

                for(let i = 0; i < text.length; i++) {
                    message.textContent += text.charAt(i);
                    scrollToBottom();
                    await new Promise(r => setTimeout(r, 15)); // vitesse d'affichage ici
                }
            }

            // Envoi message au serveur
            async function sendMessage(promptText) {
                addMessage(promptText, "user");
                scrollToBottom();
                promptInput.value = "";
                addMessage("⏳ HBA-ASSISTANT réfléchit...", "bot");
                scrollToBottom();

                try {
                    const response = await fetch("/chat", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ 
                            prompt: promptText,
                            style: styleSelect.value
                        }),
                    });
                    const data = await response.json();
                    removeLastBotMessage();
                    await displayProgressive(data.response, "bot");
                } catch (error) {
                    removeLastBotMessage();
                    addMessage("❌ Une erreur est survenue. Veuillez réessayer.", "bot");
                    scrollToBottom();
                }
            }

            // Événement entrée clavier
            promptInput.addEventListener("keydown", async (e) => {
                if (e.key === "Enter" && promptInput.value.trim() !== "") {
                    await sendMessage(promptInput.value.trim());
                }
            });

            // Reconnaissance vocale
            let recognition;
            let recognizing = false;
            if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
                const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
                recognition = new SpeechRecognition();
                recognition.lang = "fr-FR";
                recognition.interimResults = false;
                recognition.maxAlternatives = 1;

                recognition.onresult = async (event) => {
                    const transcript = event.results[0][0].transcript.trim();
                    if(transcript.length === 0) return;
                    await sendMessage(transcript);
                };

                recognition.onstart = () => {
                    recognizing = true;
                    recordBtn.textContent = "⏹️";
                };

                recognition.onend = () => {
                    recognizing = false;
                    recordBtn.textContent = "🎤";
                };

                recognition.onerror = (event) => {
                    recognizing = false;
                    recordBtn.textContent = "🎤";
                    console.error("Erreur reconnaissance vocale:", event.error);
                };

                recordBtn.addEventListener("click", () => {
                    if(recognizing) {
                        recognition.stop();
                    } else {
                        recognition.start();
                    }
                });
            } else {
                recordBtn.disabled = true;
                recordBtn.title = "Reconnaissance vocale non supportée par ce navigateur";
            }

            // Enregistrer conversation dans un fichier .txt
            saveBtn.addEventListener("click", () => {
                let textToSave = "";
                const messages = document.querySelectorAll(".message");
                messages.forEach(msg => {
                    const sender = msg.classList.contains("user") ? "User" : "Bot";
                    textToSave += `${sender}: ${msg.textContent}\n`;
                });
                const blob = new Blob([textToSave], {type: "text/plain"});
                const url = URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = "conversation_hba.txt";
                document.body.appendChild(a);
                a.click();
                a.remove();
                URL.revokeObjectURL(url);
            });

        </script>
    </body>
    </html>
    """
