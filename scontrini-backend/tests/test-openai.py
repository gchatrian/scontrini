"""
Test OpenAI API
Esegui: python test_openai.py
"""
import os
from dotenv import load_dotenv
from openai import OpenAI

# Carica .env
load_dotenv()

print("🔍 Testing OpenAI API...")

# Credenziali
api_key = os.getenv("OPENAI_API_KEY")
model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

print(f"Model: {model}")
print(f"API Key: {api_key[:20]}..." if api_key else "❌ API Key not found")

if not api_key:
    print("❌ OPENAI_API_KEY non trovata nel .env")
    exit(1)

# Crea client OpenAI
try:
    client = OpenAI(api_key=api_key)
    print("✅ OpenAI client created successfully")
except Exception as e:
    print(f"❌ Error creating OpenAI client: {e}")
    exit(1)

# Test 1: Chiamata semplice
print("\n📝 Test 1: Chiamata semplice...")
try:
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "Sei un assistente utile."},
            {"role": "user", "content": "Rispondi solo con 'OK' se funzioni correttamente."}
        ],
        max_tokens=10
    )
    
    answer = response.choices[0].message.content
    print(f"✅ Risposta: {answer}")
    print(f"📊 Tokens usati: {response.usage.total_tokens}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)

# Test 2: Test normalizzazione prodotto (simile al nostro use case)
print("\n📝 Test 2: Normalizzazione prodotto...")
try:
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system", 
                "content": "Sei un esperto di prodotti da supermercato. Normalizza i nomi dei prodotti."
            },
            {
                "role": "user", 
                "content": "Normalizza questo prodotto: 'COCA COLA 1.5L'. Rispondi in formato JSON con: {\"canonical_name\": \"...\", \"brand\": \"...\", \"category\": \"...\", \"size\": \"...\"}"
            }
        ],
        max_tokens=150
    )
    
    answer = response.choices[0].message.content
    print(f"✅ Risposta:\n{answer}")
    print(f"📊 Tokens usati: {response.usage.total_tokens}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)

# Test 3: Function calling (per Task 5)
print("\n📝 Test 3: Function calling...")
try:
    # Definiamo una funzione di test
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_product_info",
                "description": "Ottieni informazioni su un prodotto",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "product_name": {
                            "type": "string",
                            "description": "Nome del prodotto"
                        }
                    },
                    "required": ["product_name"]
                }
            }
        }
    ]
    
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "user", "content": "Cerca informazioni sulla Coca-Cola"}
        ],
        tools=tools,
        tool_choice="auto"
    )
    
    # Verifica se ha chiamato la funzione
    if response.choices[0].message.tool_calls:
        print("✅ Function calling funziona!")
        tool_call = response.choices[0].message.tool_calls[0]
        print(f"Funzione chiamata: {tool_call.function.name}")
        print(f"Parametri: {tool_call.function.arguments}")
    else:
        print("⚠️  Function calling non attivato (normale per questo test)")
    
except Exception as e:
    print(f"❌ Error: {e}")

print("\n🎉 OpenAI API test completato con successo!")
print("✅ Puoi procedere con il Task 5 (Agente normalizzazione)")
print(f"\n💰 Stima costo test: ~$0.001 (circa 200-300 tokens totali)")
