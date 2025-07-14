# Travel AI Assistant 🌍✈️

Assistente AI per pianificare viaggi personalizzati in base a preferenze e budget.

## Indice

- [Caratteristiche](#caratteristiche)
- [Architettura del Sistema](#architettura-del-sistema)
- [Installazione](#installazione)
- [Configurazione](#configurazione)
- [Utilizzo](#utilizzo)
- [Componenti Tecnici](#componenti-tecnici)
- [Struttura del Database](#struttura-del-database)
- [Esempi di Utilizzo](#esempi-di-utilizzo)
- [Workflow](#Workflow)
- [Limitazioni](#limitazioni)

## Caratteristiche

- **Consulenza personalizzata**: Memorizza preferenze e storico dell'utente
- **Ricerca alloggi**: Integrazione con Booking.com tramite web scraping
- **Previsioni meteo**: Dati meteorologici per destinazioni specifiche
- **Informazioni geografiche**: Dettagli su paesi, valute, lingue e fusi orari
- **Gestione budget**: Suggerimenti per ottimizzare le spese di viaggio
- **Memoria persistente**: Salvataggio delle conversazioni e preferenze utente

## Architettura del Sistema

### Componenti Principali

1. **Agent Core**: Basato su Agno framework con modello Google Gemini
2. **Memory System**: Gestione memoria utente e sessioni con SQLite
3. **Tool Integration**: Moduli specializzati per diverse funzionalità
4. **Storage Layer**: Persistenza dati con database SQLite

## Installazione

### Procedura di Installazione

1. **Clona il repository**:
   ```bash
   git clone https://github.com/LeoneLuca/travel-ai-assistant.git
   cd travel-ai-assistant
   ```

2. **Crea ambiente virtuale**:
   ```bash
   uv venv .venv
   .venv\Scripts\activate     # Windows
   ```

3. **Installa dipendenze**:
   ```bash
   pip install -r requirements.txt
   ```

## Configurazione

### Variabili d'Ambiente

Crea un file `.env` nella root del progetto:

```env
GOOGLE_API_KEY=your_google_api_key_here
OPENWEATHER_API_KEY=your_openweather_api_key_here
APIFY_TOKEN=your_apify_token_here
```

### Ottenimento delle Chiavi API

1. **Google API Key**: [Google AI Studio](https://makersuite.google.com/)
2. **OpenWeather API**: [OpenWeatherMap](https://openweathermap.org/api)
3. **Apify Token**: [Apify Console](https://console.apify.com/)

## Utilizzo

### Avvio dell'Applicazione

```bash
python travel_agent.py
```

### Interfaccia Utente

1. Inserisci il tuo ID utente per personalizzazione
2. Inizia a chattare con l'assistente
3. Digita "exit" per terminare

## Componenti Tecnici

### 1. Memory System

- **SqliteStorage**: Gestione sessioni conversazionali
- **SqliteMemoryDb**: Memoria persistente utente
- **Memory**: Coordinamento tra diversi tipi di memoria

### 2. Tools

#### BookingScraperTool
- **Funzione**: Ricerca alloggi su Booking.com tramite scraper
- **Input**: Città, date, ospiti, budget
- **Output**: Lista alloggi formattata con prezzi e link

#### DestinationInfoTool
- **Funzione**: Informazioni geografiche sui paesi
- **Input**: Nome paese
- **Output**: Capitale, valuta, lingua, fuso orario

#### TodayTool
- **Funzione**: Riferimento temporale per calcoli date
- **Output**: Data corrente in formato ISO

### 3. External APIs

- **OpenWeather**: Previsioni meteorologiche
- **RestCountries**: Informazioni geografiche
- **Apify**: Web scraping Booking.com
- **Google Search**: Ricerche generiche

## Struttura del Database

### Tabelle Principali

```sql
-- Sessioni Agent
CREATE TABLE travel_sessions (
    id INTEGER PRIMARY KEY,
    session_id TEXT,
    user_id TEXT,
    data JSON,
    created_at TIMESTAMP
);

-- Memoria Utente
CREATE TABLE travel_user_memory (
    id INTEGER PRIMARY KEY,
    user_id TEXT,
    memory_type TEXT,
    content JSON,
    timestamp TIMESTAMP
);
```

## Esempi di Utilizzo

### Esempio 1: Pianificazione Viaggio Completo

**Input Utente**: "Voglio andare a Tokyo per 7 giorni a marzo, budget 2000€"

**Processo dell'Agent**:
1. Raccoglie informazioni su Tokyo (DestinationInfoTool)
2. Verifica meteo per marzo (OpenWeatherTools)
3. Cerca alloggi nel budget (BookingScraperTool)
4. Fornisce itinerario personalizzato

### Esempio 2: Ricerca Alloggi Specifica

**Input Utente**: "Cerca hotel a Barcellona dal 10 al 15 giugno 2026, 2 adulti, budget 100€/notte"

**Parametri Tool**:
```python
{
    "city": "Barcelona",
    "checkIn": "2026-06-10",
    "checkOut": "2026-06-15",
    "adults": 2,
    "minMaxPrice": "80-120"
}
```

### Esempio 3: Consulenza Meteo

**Input Utente**: "Che tempo farà a Londra la prossima settimana?"

**Risposta**: Previsioni dettagliate con temperature, precipitazioni e consigli di abbigliamento.

## Workflow

1. **Inizializzazione**: Caricamento memoria utente
2. **Analisi Richiesta**: Comprensione intent e parametri
3. **Tool Selection**: Scelta strumenti appropriati
4. **Data Gathering**: Raccolta informazioni esterne
5. **Processing**: Elaborazione e sintesi dati
6. **Response Generation**: Creazione risposta personalizzata
7. **Memory Update**: Aggiornamento preferenze utente

## Limitazioni

### Limitazioni Attuali

- Dipendenza da API esterne per funzionalità complete
- Scraping limitato a 3 risultati per ricerca alloggi
- Previsioni meteo accurate solo per 7 giorni
