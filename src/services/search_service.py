import os
from elasticsearch import Elasticsearch
from src.config.settings import PAGE_SIZE
from typing import List, Dict
from src.utils.helpers import sanitize_for_es

ELASTIC_HOST = os.environ.get("ELASTIC_HOST", "http://localhost:9200")
INDEX_NAME = "products_customer"

try:
    es_client = Elasticsearch(hosts=[ELASTIC_HOST])
    if not es_client.ping():
        raise ConnectionError("Không thể kết nối đến Elasticsearch từ search_service.")
except ConnectionError as e:
    print(f"Lỗi kết nối trong search_service: {e}")
    es_client = None

def search_products(customer_id: str, product_name: str = None, category: str = None, properties: str = None, offset: int = 0, size: int = PAGE_SIZE, strict_properties: bool = False, strict_category: bool = False) -> List[Dict]:
    if not customer_id:
        print("Lỗi: customer_id là bắt buộc để tìm kiếm.")
        return []
        
    if not product_name and not category and not properties:
        return []

    sanitized_customer_id = sanitize_for_es(customer_id)

    body = {
        "query": {
            "bool": {
                "must": [],
                "should": [],
                "filter": [
                    {"term": {"customer_id": sanitized_customer_id}}
                ]
            }
        },
        "size": size,
        "from": offset
    }

    if product_name:
        body["query"]["bool"]["must"].append({
            "match": {
                "product_name": {
                    "query": product_name
                }
            }
        })
        body["query"]["bool"]["should"].append({
            "match_phrase": {
                "product_name": {
                    "query": product_name,
                    "boost": 10.0
                }
            }
        })

    if category:
        cat_field = "category.keyword" if strict_category else "category"
        if strict_category:
            body["query"]["bool"]["must"].append({"match": {cat_field: category}})
        else:
            body["query"]["bool"]["should"].append({"match": {cat_field: {"query": category, "boost": 5.0}}})

    if properties:
        prop_query = {"match": {"properties": {"query": properties, "operator": "and"}}}
        if strict_properties:
            body["query"]["bool"]["must"].append(prop_query)
        else:
            body["query"]["bool"]["should"].append(prop_query)

    try:
        response = es_client.search(
            index=INDEX_NAME,
            body=body,
            routing=sanitized_customer_id
        )
        hits = [hit['_source'] for hit in response['hits']['hits']]
        print(f"Tìm thấy {len(hits)} sản phẩm cho customer '{customer_id}' (offset={offset}, strict_cat={strict_category}, strict_prop={strict_properties}).")
        return hits
    except Exception as e:
        print(f"Lỗi khi tìm kiếm cho customer '{customer_id}': {e}")
        return []
    
def search_products_by_image(customer_id: str, image_embedding: list, top_k: int = 1, min_similarity: float = 0.97) -> list:
    """
    Thực hiện tìm kiếm k-Nearest Neighbor (kNN) trong Elasticsearch
    để tìm các sản phẩm có ảnh tương đồng nhất.
    Chỉ trả về kết quả nếu độ tương đồng cao hơn một ngưỡng nhất định.
    """
    if not customer_id:
        print("Lỗi: customer_id là bắt buộc để tìm kiếm bằng hình ảnh.")
        return []
    if not image_embedding:
        return []

    sanitized_customer_id = sanitize_for_es(customer_id)

    knn_query = {
        "field": "image_embedding", 
        "query_vector": image_embedding,
        "k": top_k,
        "num_candidates": 100 
    }
    
    query = {
        "term": {
            "customer_id": sanitized_customer_id
        }
    }

    try:
        response = es_client.search(
            index=INDEX_NAME,
            knn=knn_query,
            query=query,
            routing=sanitized_customer_id,
            min_score=min_similarity,
            size=top_k,
            _source_includes=[ 
                "product_name", "category", "properties", "specifications", "lifecare_price",
                "inventory", "avatar_images", "link_product"
            ]
        )
        hits = [hit['_source'] for hit in response['hits']['hits']]
        print(f"Tìm thấy {len(hits)} sản phẩm tương đồng cho customer '{customer_id}' (ngưỡng > {min_similarity}).")
        return hits
    except Exception as e:
        print(f"Lỗi khi tìm kiếm bằng vector cho customer '{customer_id}': {e}")
        return []
