from elasticsearch import AsyncElasticsearch
from src.config.settings import ELASTIC_HOST
from database.database import SessionLocal
from elastic_search_push_data import ensure_shared_indices_exist


es_client: AsyncElasticsearch = None

async def init_es_client():
    """
    Initializes and returns a single instance of the Elasticsearch client.
    """
    global es_client
    if es_client is None:
        try:
            print(f"🔌 Connecting to Elasticsearch at {ELASTIC_HOST}...")
            es_client = AsyncElasticsearch(hosts=[ELASTIC_HOST])
            if not await es_client.ping():
                raise ConnectionError("Could not connect to Elasticsearch")
            print("✅ Successfully connected to Elasticsearch!")
            print("🔧 Ensuring shared indices exist...")
            await ensure_shared_indices_exist(es_client)
            print("✅ Shared indices check completed!")
        except ConnectionError as e:
            print(f"❌ Error connecting to Elasticsearch: {e}")
            es_client = None
        except Exception as e:
            print(f"❌ Unexpected error during Elasticsearch initialization: {e}")
            es_client = None
    else:
        print("ℹ️ Elasticsearch client already initialized")

async def close_es_client():
    """
    Closes the Elasticsearch client connection.
    """
    global es_client
    if es_client:
        await es_client.close()
        es_client = None
        print("Elasticsearch client closed.")

def get_es_client() -> AsyncElasticsearch:
    """
    Dependency provider for the Elasticsearch client.
    Returns the initialized client instance.
    """
    return es_client

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()