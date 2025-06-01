from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import requests
import spacy
import pandas as pd
from typing import Dict, List
import uuid
import re
from difflib import SequenceMatcher
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()


origins = [
    "http://localhost:3000",  # or your frontend URL
    "http://localhost:8000",
    "http://localhost:8001",
    # Add other origins if needed
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Allows requests from these origins
    allow_credentials=True,
    allow_methods=["*"],    # Allow all methods (GET, POST, OPTIONS, etc)
    allow_headers=["*"],    # Allow all headers
)

# Dictionnaire global pour stocker l'historique des conversations par session
conversation_history: Dict[str, List[Dict[str, str]]] = {}

def update_history(session_id: str, user_message: str, bot_response: str):
    """Ajoute le message utilisateur et la réponse du bot à l'historique."""
    if session_id not in conversation_history:
        conversation_history[session_id] = []
    conversation_history[session_id].append({
        "user": user_message,
        "assistant": bot_response
    })

def get_history_text(session_id: str) -> str:
    """Retourne l'historique complet formaté en texte."""
    if session_id not in conversation_history:
        return ""
    history_text = ""
    for entry in conversation_history[session_id]:
        history_text += f"Utilisateur: {entry['user']}\n"
        history_text += f"Assistant: {entry['assistant']}\n\n"
    return history_text.strip()

# Charger le modèle spaCy
try:
    nlp = spacy.load('en_core_web_sm')
except OSError:
    import subprocess
    import sys
    subprocess.run([sys.executable, "-m", "spacy", "download", "en_core_web_sm"], check=True)
    nlp = spacy.load('en_core_web_sm')

OLLAMA_URL = "http://localhost:11434/api/generate"

# Chargement du fichier Excel
try:
    df = pd.read_excel(r'C:\Users\DeLL\OneDrive\Desktop\cc.xlsx')
    names_fr = df['NOM_FR'].str.lower().str.strip().tolist()
    names_ar = df['NOM_AR'].str.strip().tolist()
    print("✅ Base de données entreprises chargée")
except Exception as e:
    print(f"⚠️ Erreur chargement base de données: {e}")
    names_fr, names_ar = [], []

def similar(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()

def check_name_reserved(name: str, threshold: float = 0.85) -> bool:
    name_lower = name.lower().strip()
    
    # Vérification exacte
    if name_lower in names_fr or name_lower in [x.lower() for x in names_ar]:
        return True
    
    # Vérification par similarité
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

class ChatRequest(BaseModel):
    prompt: str
    style: str = "concise"
    session_id: str = "default"
    short_response: bool = False

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    prompt = request.prompt
    session_id = request.session_id
    style = request.style
    short = request.short_response

    # Vérification de nom d'entreprise
    extracted_name = extract_company_name(prompt)
    if extracted_name and extracted_name.strip():
        reserved = check_name_reserved(extracted_name)
        if reserved:
            return JSONResponse(content={
                "response": f"❌ Le nom '{extracted_name}' est déjà réservé. Veuillez proposer un autre nom.",
                "type": "name_check"
            })

    # Préparation du contexte historique
    history_text = get_history_text(session_id)

    # Construction du prompt final
    template = (
        "Tu es un expert en création d'entreprise en Tunisie. "
        "Fournis des informations précises sur la disponibilité des noms d'entreprise "
        "et propose 5 suggestions alternatives quand nécessaire.\n\n"
        "Historique:\n{history_text}\n\n"
        "Nouvelle question: {prompt}\n\n"
        "Réponds de manière {style} en 1-2 phrases maximum."
    )

    prompt_final = template.format(
        history_text=history_text,
        prompt=prompt,
        style=style
    )

    # Envoi à Ollama
    try:
        response = requests.post(OLLAMA_URL, json={
            "model": "llama2:7b",
            "prompt": prompt_final,
            "stream": False
        },)
        
        print(f"📡 Ollama status: {response.status_code}")
        print(f"📄 Ollama response text: {response.text}")
        
        if response.status_code != 200:
            raise Exception(f"Erreur Ollama: {response.status_code}")
            
        result = response.json()
        bot_response = result.get("response", "Désolé, je n'ai pas de réponse.").strip()
        
        update_history(session_id, prompt, bot_response)
        
        return JSONResponse(content={
            "response": bot_response,
            "type": "ollama_response"
        })
        
    except Exception as e:
        print(f"⚠️ Exception: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Erreur de traitement: {str(e)}"}
        )


# L'interface HTML reste identique (même code que dans votre dernière version)
# ...

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
