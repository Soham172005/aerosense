import logging
from typing import List, Dict, Any
from serpapi import GoogleSearch
from django.conf import settings

logger = logging.getLogger(__name__)


class ProductFetcher:
    """
    Fetches product data from Google Shopping via SerpAPI.
    Returns structured product information for air quality products.
    """
    
    def __init__(self):
        self.api_key = settings.SERPAPI_KEY
        self.engine = settings.SERPAPI_ENGINE
        self.country = settings.SERPAPI_COUNTRY
        self.language = settings.SERPAPI_LANGUAGE
    
    def fetch_products(self, query: str, max_results: int = 20) -> List[Dict[str, Any]]:
        """
        Fetch products from Google Shopping for a given query.
        
        Args:
            query: Search query (e.g., "n95 mask india")
            max_results: Maximum number of results to return
            
        Returns:
            List of product dictionaries with parsed data
        """
        try:
            params = {
                "engine": self.engine,
                "q": query,
                "api_key": self.api_key,
                "google_domain": "google.co.in",
                "gl": self.country,
                "hl": self.language,
                "num": max_results,
            }
            
            search = GoogleSearch(params)
            results = search.get_dict()
            
            # Check for errors
            if "error" in results:
                logger.error(f"SerpAPI error: {results['error']}")
                return []
            
            # Parse shopping results
            shopping_results = results.get("shopping_results", [])
            
            if not shopping_results:
                logger.warning(f"No shopping results found for query: {query}")
                return []
            
            products = []
            for item in shopping_results[:max_results]:
                product = self._parse_product(item)
                if product:
                    products.append(product)
            
            logger.info(f"Fetched {len(products)} products for query: {query}")
            return products
            
        except Exception as e:
            logger.exception(f"Error fetching products for query '{query}': {e}")
            return []
    
    def _parse_product(self, item: Dict) -> Dict[str, Any]:
        """
        Parse a single product result from SerpAPI response.
        
        Args:
            item: Raw product data from SerpAPI
            
        Returns:
            Structured product dictionary
        """
        try:
            # Extract price (use extracted_price if available, fallback to parsing)
            price = item.get("extracted_price", 0)
            if not price:
                price = self._extract_price(item.get("price", ""))
            
            # Extract rating
            rating = item.get("rating", 0)
            if isinstance(rating, str):
                try:
                    rating = float(rating)
                except:
                    rating = 0
            
            # Extract reviews count
            reviews = self._extract_reviews(item.get("reviews", 0))
            
            # Extract product URL (try multiple fields)
            product_url = (
                item.get("product_link") or 
                item.get("link") or 
                item.get("serpapi_product_api") or
                ""
            )
            
            # Extract image URL (try multiple fields)
            image_url = (
                item.get("thumbnail") or
                item.get("serpapi_thumbnail") or
                ""
            )
            
            # Build product dict
            product = {
                "name": item.get("title", "")[:256],
                "description": item.get("snippet", "")[:500],
                "price": float(price) if price else 0,
                "image_url": image_url,
                "product_url": product_url,
                "source": item.get("source", "Google Shopping")[:128],
                "rating": float(rating) if rating else 0,
                "reviews": reviews,
                "delivery": item.get("delivery", ""),
                "raw_data": item,  # Store full response for debugging
            }
            
            return product
            
        except Exception as e:
            logger.error(f"Error parsing product: {e}")
            return None
    
    def _extract_price(self, price_str: str) -> float:
        """
        Extract numeric price from price string.
        Handles formats like: "₹599", "$19.99", "Rs. 1,499"
        
        Args:
            price_str: Price string from SerpAPI
            
        Returns:
            Float price value (0 if cannot parse)
        """
        if not price_str:
            return 0
        
        try:
            # Remove currency symbols and commas
            price_str = str(price_str)
            price_str = price_str.replace("₹", "").replace("Rs.", "").replace("$", "")
            price_str = price_str.replace(",", "").strip()
            
            # Extract first number (handles ranges like "599-799")
            price_str = price_str.split("-")[0].split()[0]
            
            return float(price_str)
        except:
            return 0
    
    def _extract_reviews(self, reviews_data) -> int:
        """
        Extract numeric review count.
        Handles formats like: "2.8K", "150", 2800
        
        Args:
            reviews_data: Reviews count from SerpAPI (string or int)
            
        Returns:
            Integer review count
        """
        if not reviews_data:
            return 0
        
        try:
            # If already int
            if isinstance(reviews_data, int):
                return reviews_data
            
            # If string
            reviews_str = str(reviews_data).upper().strip()
            
            # Handle K (thousands)
            if "K" in reviews_str:
                reviews_str = reviews_str.replace("K", "").strip()
                return int(float(reviews_str) * 1000)
            
            # Handle M (millions)
            if "M" in reviews_str:
                reviews_str = reviews_str.replace("M", "").strip()
                return int(float(reviews_str) * 1000000)
            
            # Remove commas and convert
            reviews_str = reviews_str.replace(",", "")
            return int(float(reviews_str))
            
        except:
            return 0
    
    def fetch_all_categories(self) -> Dict[str, List[Dict]]:
        """
        Fetch products for all predefined categories.
        
        Returns:
            Dictionary mapping category name to list of products
        """
        categories = {
            "mask": [
                "n95 mask india",
                "n99 anti pollution mask india",
                "reusable pollution mask india",
            ],
            "purifier": [
                "air purifier india hepa",
                "best air purifier india 2024",
                "air purifier under 20000",
            ],
            "room_purifier": [
                "room air purifier india",
                "bedroom air purifier best",
                "portable air purifier india",
            ],
            "monitor": [
                "air quality monitor india pm2.5",
                "aqi meter india",
                "indoor air quality monitor",
            ],
            "car-filter": [
                "car air purifier india best",
                "vehicle cabin air filter",
                "car ionizer air purifier",
            ],
            "plant": [
                "air purifying indoor plants india",
                "snake plant india online",
                "money plant for home india",
            ],
        }
        
        all_products = {}
        
        for category, queries in categories.items():
            logger.info(f"Fetching products for category: {category}")
            category_products = []
            
            for query in queries:
                products = self.fetch_products(query, max_results=10)
                category_products.extend(products)
            
            # Remove duplicates by name
            seen = set()
            unique_products = []
            for p in category_products:
                name = p.get("name", "").lower()
                if name and name not in seen:
                    seen.add(name)
                    unique_products.append(p)
            
            all_products[category] = unique_products
            logger.info(f"Category '{category}': {len(unique_products)} unique products")
        
        return all_products


# Convenience function for direct import
def fetch_products_by_query(query: str, max_results: int = 20) -> List[Dict]:
    """
    Convenience function to fetch products without instantiating class.
    
    Usage:
        from aqi_app.services.product_fetcher import fetch_products_by_query
        products = fetch_products_by_query("n95 mask india")
    """
    fetcher = ProductFetcher()
    return fetcher.fetch_products(query, max_results)


def fetch_all_products() -> Dict[str, List[Dict]]:
    """
    Convenience function to fetch all category products.
    
    Usage:
        from aqi_app.services.product_fetcher import fetch_all_products
        all_products = fetch_all_products()
    """
    fetcher = ProductFetcher()
    return fetcher.fetch_all_categories()