
import json
import time
import requests
from rich.pretty import pprint
from agno.agent import Agent
from agno.models.google import Gemini
from agno.storage.sqlite import SqliteStorage
from agno.memory.v2.db.sqlite import SqliteMemoryDb
from agno.memory.v2.memory import Memory
from agno.tools.reasoning import ReasoningTools
from agno.tools.googlesearch import GoogleSearchTools
from agno.tools.openweather import OpenWeatherTools
from agno.tools import tool
from agno.playground import Playground, serve_playground_app
from datetime import date
from dotenv import load_dotenv
import os

# Carica chiavi da .env
load_dotenv()

DB_FILE = "tmp/travel_memories.sqlite"
AGENT_SESSIONS_TABLE = "travel_sessions"
USER_MEMORIES_TABLE = "travel_user_memory"
ACTOR_ID = "voyager~booking-scraper"

today = date.today().isoformat()

# Crea cartella tmp se non esiste
os.makedirs("tmp", exist_ok=True)

# Configurazione storage
storage = SqliteStorage(
    db_file = DB_FILE,
    table_name = AGENT_SESSIONS_TABLE
)

# Configurazione memoria utente
memory = Memory(
    db=SqliteMemoryDb(
        db_file=DB_FILE,
        table_name=USER_MEMORIES_TABLE
    ),
    delete_memories=False,
    clear_memories=False,
)

#memory.clear()

@tool # Definisce un tool per ottenere informazioni su un paese
def DestinationInfoTool(country: str) -> dict:
    """
    Ottieni informazioni generali su un paese
    
    Args:
        country: Nome del paese
    
    Returns:
        dict: Informazioni su valuta, lingua, fuso orario, etc.
    """
    try:
        url = f"https://restcountries.com/v3.1/name/{country}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()[0]
            return {
                'name': data['name']['common'],
                'capital': data.get('capital', ['N/A'])[0],
                'currency': list(data.get('currencies', {}).keys())[0] if data.get('currencies') else 'N/A',
                'language': list(data.get('languages', {}).values())[0] if data.get('languages') else 'N/A',
                'timezone': data.get('timezones', ['N/A'])[0],
                'population': data.get('population', 'N/A')
            }
        else:
            return {"error": "Paese non trovato"}
    except Exception as e:
        return {"error": f"Errore info paese: {str(e)}"}

@tool
def TodayTool() -> str:
    """
    Restituisce la data odierna in formato ISO (YYYY-MM-DD)
    
    Returns:
        str: Data odierna
    """
    return today

@tool # Definisce un tool per cercare alloggi su Booking.com
def BookingScraperTool(params: dict) -> str:
    """
    Scrape alloggi da Booking.com usando Apify (sandbox actor)

    Args:
        params: dizionario con i seguenti campi:
            - city (str): città richiesta (obbligatorio)
            - checkIn (str): data check-in in formato YYYY-MM-DD (opzionale)
            - checkOut (str): data check-out in formato YYYY-MM-DD (opzionale)
            - adults (int): numero di adulti (opzionale)
            - children (int): numero di bambini (opzionale) 
            - minMaxPrice (str): intervallo prezzi in formato "min-max", es. "50-150" (opzionale)

    Returns: stringa con le opzioni di alloggio trovate
    """
    try:
        city = params.get("city")
        if not city:
            return "Campo 'city' obbligatorio."
        
        checkin = params.get("checkIn")
        checkout = params.get("checkOut")
        adults = params.get("adults")
        children = params.get("children")
        minmax = params.get("minMaxPrice")

        # URL per avviare l'actor
        run_url = f"https://api.apify.com/v2/acts/{ACTOR_ID}/runs?token={os.getenv('APIFY_TOKEN')}"

        # Payload per l'actor
        payload = {
            "search": city,
            "maxItems": 3,
            #"sortBy": "distance_from_search",
            "currency": "EUR",
            "language": "it"
        }
        
        if checkin: payload["checkIn"] = checkin
        if checkout: payload["checkOut"] = checkout
        if adults: payload["adults"] = adults
        if children: payload["children"] = children
        if minmax: payload["minMaxPrice"] = minmax

        headers = {"Content-Type": "application/json"}
        
        # Avvia l'actor
        print(f"Cercando alloggi per {city}...")
        response = requests.post(run_url, data=json.dumps(payload), headers=headers)
        response.raise_for_status()

        run_data = response.json()
        run_id = run_data.get("data", {}).get("id")
        
        if not run_id:
            return f"Errore nell'avvio della ricerca per {city}"

        # Attende completamento dell'actor
        status_url = f"https://api.apify.com/v2/acts/{ACTOR_ID}/runs/{run_id}?token={os.getenv('APIFY_TOKEN')}"
                
        max_wait = 60  # Attesa massima di 60 secondi
        wait_time = 0
        
        while wait_time < max_wait:
            status_response = requests.get(status_url)
            status_response.raise_for_status()
            status_data = status_response.json()
            
            status = status_data.get("data", {}).get("status")
            print(f"Status: {status}")
            
            if status == "SUCCEEDED":
                break
            elif status == "FAILED":
                return f"Ricerca fallita per {city}"
            
            time.sleep(5)
            wait_time += 5
        
        if wait_time >= max_wait:
            return f"Timeout nella ricerca per {city}"
        
        # Ottieni i risultati
        dataset_id = status_data.get("data", {}).get("defaultDatasetId")
        
        if not dataset_id:
            return f"Nessun dataset trovato per {city}"
        
        dataset_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items?token={os.getenv('APIFY_TOKEN')}"
        
        dataset_response = requests.get(dataset_url)
        dataset_response.raise_for_status()
        
        data = dataset_response.json()
        
        if not data:
            return f"🔍 Nessun alloggio trovato per {city}"

        # Formatta i risultati
        lines = [f"**Alloggi trovati per {city}**"]
        
        if checkin and checkout:
            lines.append(f"Dal {checkin} al {checkout}")
        
        lines.append("")

        for i, hotel in enumerate(data[:5], 1):
            name = hotel.get("name") or hotel.get("title") or "Nome non disponibile"
            
            # Gestione prezzo
            price = hotel.get("price")
            if price:
                currency = hotel.get("currency", "EUR")
                price_str = f"{price} {currency} (totale per il soggiorno)"
            else:
                price_str = "Prezzo su richiesta"
            
            # Distanza dal centro
            distance = hotel.get("distanceFromCenter")
            distance_str = f"{distance}" if distance else ""
            
            # URL
            url = hotel.get("url", "")
            
            lines.append(f"{i}. **{name}**")
            lines.append(f"{price_str}")
            if distance_str:
                lines.append(f"{distance_str}")
            if url:
                lines.append(f"{url}")
            lines.append("")

        return "\n".join(lines)

    except requests.exceptions.RequestException as e:
        return f"Errore di connessione: {str(e)}"
    except Exception as e:
        return f"Errore generale: {str(e)}"

# Configurazione istruzioni
TRAVEL_INSTRUCTIONS =  """
Sei un consulente di viaggio esperto e appassionato. Il tuo obiettivo è creare esperienze di viaggio memorabili e personalizzate. 

Ricorda tutte le preferenze di viaggio e le destinazioni dell'utente per future consultazioni e utilizza sempre quello che sai dell'utente.

1. RACCOLTA INFORMAZIONI:
   - Chiedi sempre: destinazione, date, durata, budget, interessi principali
   - Identifica il tipo di viaggiatore: avventuriero, culturale, relax, famiglia, business
   - Scopri preferenze su trasporti, alloggi, cucina locale
   - Verifica se ci sono esigenze speciali o limitazioni

2. RICERCA E ANALISI:
   - Controlla sempre il meteo per le date del viaggio
   - Ricerca eventi, festival o stagionalità della destinazione
   - Verifica documentazione necessaria (visti, vaccini)
   - Analizza i costi realistici per la destinazione

3. CREAZIONE ITINERARIO:
   - Bilancia must-see e esperienze autentiche locali
   - Ottimizza gli spostamenti per ridurre tempi morti
   - Includi tempo per riposo e flessibilità
   - Proponi alternative per diversi budget e meteo

4. GESTIONE BUDGET:
   - Suddividi il budget in: trasporti, alloggi, cibo, attività, emergenze
   - Suggerisci quando prenotare per risparmiare
   - Proponi alternative economiche senza compromettere l'esperienza
   - Monitora i costi durante la pianificazione

5. COMUNICAZIONE:
    - Rispondi sempre in italiano
   - Usa un tono entusiasta ma professionale
   - Fornisci informazioni pratiche concrete
   - Spiega il reasoning dietro ogni raccomandazione
   - Offri sempre opzioni alternative

Utilizza i tools a disposizione per ottenere informazioni sui luoghi, il meteo e le opzioni d'alloggio.

Confronta sempre tutte le date con la data odierna usando sempre e solo il tool TodayTool.
Se l'utente fornisce una data senza anno (es. "10 agosto"), considera sempre l'anno corrente o, se la data è già passata, l'anno successivo.

Nota: 
    - l'input minMaxPrice del tool BookingScraperTool è il range di prezzo per notte.
    - il campo "price" fornito dalla ricerca del tool BookingScraperTool si riferisce al **totale del soggiorno**, non al prezzo per notte. Se vuoi confrontare con un budget giornaliero, devi dividere per il numero di notti.
    - Non mostrare mai i risultati di ricerca di BookingScraperTool se non sono adatti a soddisfare le richieste dell'utente.
    - fornisci sempre l'url dell'alloggio per ulteriori dettagli.
    - il tool OpenWeatherTools fornisce previsioni meteo dettagliate solo per i 7 giorni successivi, utilizza i dati dell'anno precedente per stimare il meteo.
    - il tool DestinationInfoTool fornisce informazioni generali su un paese, come valuta, lingua, fuso orario e popolazione.

"""

# Configurazione agente
travel_agent = Agent(
    name = "Travel Planning Assistant",
    model = Gemini(api_key=os.getenv("GOOGLE_API_KEY")),
    tools=[OpenWeatherTools(api_key=os.getenv("OPENWEATHER_API_KEY")), DestinationInfoTool, TodayTool, BookingScraperTool],
    show_tool_calls=True,
    instructions = TRAVEL_INSTRUCTIONS,
    storage = storage,
    memory = memory,
    enable_agentic_memory=True,
    enable_user_memories=True,
    markdown=True,
    add_history_to_messages=True,
    debug_mode = False
)

# Configura l'agente per l'interfaccia Playground
#playground = Playground(agents=[travel_agent]).get_app()

if __name__ == "__main__":
    # Avvia l'applicazione Playground
    #playground = serve_playground_app(playground)

    print("=== TRAVEL PLANNING ASSISTANT ===")
    print("Il tuo consulente di viaggio personale")
    
    user_id = input("\nInserisci il tuo ID: ").strip()
    
    if not user_id:
        print("ID richiesto per personalizzare le raccomandazioni.")
        exit(1)
    
    print(f"\nBenvenuto {user_id}! I tuoi profili di viaggio sono memorizzati in sicurezza.")
    print("Posso aiutarti con:")
    print("- Pianificazione itinerari personalizzati")
    print("- Controllo meteo e condizioni di viaggio")
    print("- Gestione budget e consigli di risparmio")
    print("- Informazioni su destinazioni e cultura locale\n")
    
    #DEBUG: Stampa le memorie utente
    #print(f"Memorie utente per {user_id}:")
    #pprint(memory.get_user_memories(user_id=user_id))
    
    travel_agent.cli_app(user=user_id, user_id=user_id, exit_on="exit")
