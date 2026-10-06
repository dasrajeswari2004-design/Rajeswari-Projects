#Chroma DB connections and operations for product data
from app.extensions import chroma_client


class ChromaProducts:
    def __init__(self):
        self.chroma_client = chroma_client
        self.collection_name = "products_collection"
        self.collection = self.chroma_client.get_or_create_collection(
            self.collection_name
        )


    def create_collection(self):
        self.collection = self.chroma_client.get_or_create_collection(
            self.collection_name
        )

    def insert_product(self, product_data):
        self.collection.add(
            ids=[str(product_data["id"])],
            documents=[product_data["name"] + " " + product_data["description"]],
            metadatas=[{
                "name": product_data["name"],
                "category": product_data["category"],
            }],
        )

    def get_product(self, product_id):
        return self.collection.get(ids=[str(product_id)])

    def search_products(self, query):
        results = self.collection.query(query_texts=[query], n_results=2)
        return [
            {"id": product_id}
            for product_id in results.get("ids", [[]])[0]
        ]

    def update_product(self, product_id, updated_data):
        self.collection.update(
            ids=[str(product_id)],
            documents=[updated_data["name"] + " " + updated_data["description"]],
            metadatas=[{
                "name": updated_data["name"],
                "category": updated_data["category"],
            }],
        )

    def delete_product(self, product_id):
        self.collection.delete(ids=[str(product_id)])