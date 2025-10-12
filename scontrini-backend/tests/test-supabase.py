"""
Test connessione Supabase
Esegui: python test_supabase.py
"""
import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Carica .env
load_dotenv()

# Credenziali
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

print("🔍 Testing Supabase connection...")
print(f"URL: {SUPABASE_URL}")

# Crea client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Test 1: Connessione base
print("\n✅ Supabase client created successfully")

# Test 2: Query alle tabelle
try:
    # Query households (dovrebbe essere vuota)
    response = supabase.table("households").select("*").execute()
    print(f"✅ Query households: {len(response.data)} records")
    
    # Query receipts (dovrebbe essere vuota)
    response = supabase.table("receipts").select("*").execute()
    print(f"✅ Query receipts: {len(response.data)} records")
    
    # Query normalized_products (dovrebbe essere vuota)
    response = supabase.table("normalized_products").select("*").execute()
    print(f"✅ Query normalized_products: {len(response.data)} records")
    
    print("\n🎉 Supabase connection working perfectly!")
    print("📊 Database is ready to use")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    print("Verifica che le tabelle siano state create correttamente")
