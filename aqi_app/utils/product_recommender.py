import logging
from typing import List, Dict, Optional
from django.db.models import Q
from aqi_app.models import Product

logger = logging.getLogger(__name__)


class ProductRecommender:
    """
    Recommends air quality products based on AQI levels and user conditions.
    """
    
    # AQI Category Definitions
    AQI_CATEGORIES = {
        "good": (0, 50),
        "moderate": (51, 100),
        "unhealthy_sensitive": (101, 150),
        "unhealthy": (151, 200),
        "very_unhealthy": (201, 300),
        "hazardous": (301, 500),
    }
    
    # Product type priorities by AQI level
    PRODUCT_PRIORITIES = {
        "good": ["plant", "monitor"],
        "moderate": ["mask", "plant", "monitor"],
        "unhealthy_sensitive": ["mask", "purifier", "room_purifier", "monitor"],
        "unhealthy": ["mask", "purifier", "room_purifier", "monitor", "car-filter"],
        "very_unhealthy": ["purifier", "room_purifier", "mask", "monitor", "car-filter"],
        "hazardous": ["purifier", "room_purifier", "mask", "monitor", "car-filter", "plant"],
    }
    
    def __init__(self):
        pass
    
    def get_aqi_category(self, aqi: int) -> str:
        """
        Get AQI category name from AQI value.
        
        Args:
            aqi: AQI value (0-500)
            
        Returns:
            Category name string
        """
        if aqi <= 50:
            return "good"
        elif aqi <= 100:
            return "moderate"
        elif aqi <= 150:
            return "unhealthy_sensitive"
        elif aqi <= 200:
            return "unhealthy"
        elif aqi <= 300:
            return "very_unhealthy"
        else:
            return "hazardous"
    
    def get_recommendations(
        self, 
        aqi: int, 
        category: Optional[str] = None,
        max_results: int = 50,
        user_conditions: Optional[List[str]] = None
    ) -> List[Product]:
        """
        Get product recommendations based on AQI level.
        
        Args:
            aqi: Current AQI value
            category: Optional filter by product type (mask/purifier/etc)
            max_results: Maximum number of products to return
            user_conditions: Optional list of user health conditions
            
        Returns:
            List of Product model instances, ordered by relevance
        """
        try:
            # Get AQI category
            aqi_category = self.get_aqi_category(aqi)
            
            logger.info(f"Getting recommendations for AQI {aqi} (category: {aqi_category})")
            
            # Base query: products within AQI range
            query = Q(aqi_min__lte=aqi) & Q(aqi_max__gte=aqi)
            
            # Filter by category if provided
            if category:
                query &= Q(product_type=category)
            
            products = Product.objects.filter(query)
            
            # If no products found in exact range, expand search
            if not products.exists():
                logger.warning(f"No products found for AQI {aqi}, expanding search...")
                products = Product.objects.filter(aqi_min__lte=aqi + 50)
            
            # Order by priority
            priority_types = self.PRODUCT_PRIORITIES.get(aqi_category, [])
            
            # Custom ordering by product type priority
            ordered_products = []
            for ptype in priority_types:
                type_products = products.filter(product_type=ptype).order_by('-effectiveness', '-rating')
                ordered_products.extend(list(type_products))
            
            # Add remaining products not in priority list
            remaining = products.exclude(
                product_type__in=priority_types
            ).order_by('-effectiveness', '-rating')
            ordered_products.extend(list(remaining))
            
            # Remove duplicates while preserving order
            seen = set()
            unique_products = []
            for p in ordered_products:
                if p.id not in seen:
                    seen.add(p.id)
                    unique_products.append(p)
            
            # Apply user condition boosting (if provided)
            if user_conditions:
                unique_products = self._boost_for_conditions(unique_products, user_conditions)
            
            result = unique_products[:max_results]
            
            logger.info(f"Returning {len(result)} recommended products")
            return result
            
        except Exception as e:
            logger.exception(f"Error getting recommendations: {e}")
            return []
    
    def _boost_for_conditions(
        self, 
        products: List[Product], 
        conditions: List[str]
    ) -> List[Product]:
        """
        Boost products that are recommended for specific health conditions.
        
        Args:
            products: List of Product instances
            conditions: List of condition strings (e.g., ["asthma", "elderly"])
            
        Returns:
            Reordered list with boosted products first
        """
        boosted = []
        normal = []
        
        for product in products:
            recommended_for = product.recommended_for or []
            
            # Check if any user condition matches product recommendations
            if any(cond.lower() in str(recommended_for).lower() for cond in conditions):
                boosted.append(product)
            else:
                normal.append(product)
        
        return boosted + normal
    
    def get_category_recommendations(
        self, 
        aqi: int, 
        product_type: str,
        max_results: int = 20
    ) -> List[Product]:
        """
        Get recommendations for a specific product category.
        
        Args:
            aqi: Current AQI value
            product_type: Product type (mask/purifier/monitor/car-filter/plant)
            max_results: Maximum products to return
            
        Returns:
            List of Product instances
        """
        return self.get_recommendations(aqi, category=product_type, max_results=max_results)
    
    def get_recommendation_message(self, aqi: int) -> Dict[str, str]:
        """
        Get human-readable recommendation message for AQI level.
        
        Args:
            aqi: Current AQI value
            
        Returns:
            Dictionary with category, message, and recommended actions
        """
        category = self.get_aqi_category(aqi)
        
        messages = {
            "good": {
                "category": "Good",
                "message": "Air quality is satisfactory. No special precautions needed.",
                "recommendation": "Consider air quality monitors to track changes and indoor plants for additional freshness.",
                "color": "green",
            },
            "moderate": {
                "category": "Moderate",
                "message": "Air quality is acceptable for most people.",
                "recommendation": "Sensitive individuals should consider wearing masks during prolonged outdoor activities. Basic air purifiers recommended for homes.",
                "color": "yellow",
            },
            "unhealthy_sensitive": {
                "category": "Unhealthy for Sensitive Groups",
                "message": "Sensitive groups (children, elderly, respiratory patients) may experience health effects.",
                "recommendation": "N95 masks essential for outdoor activities. HEPA air purifiers strongly recommended for indoor spaces. Consider air quality monitors.",
                "color": "orange",
            },
            "unhealthy": {
                "category": "Unhealthy",
                "message": "Everyone may begin to experience health effects.",
                "recommendation": "N95/N99 masks mandatory outdoors. Premium air purifiers with HEPA filters essential. Limit outdoor activities. Use car air filters.",
                "color": "red",
            },
            "very_unhealthy": {
                "category": "Very Unhealthy",
                "message": "Health alert: everyone may experience serious health effects.",
                "recommendation": "Stay indoors. Use N99 masks if must go outside. Premium air purifiers running continuously. Seal windows and doors. Monitor indoor AQI.",
                "color": "purple",
            },
            "hazardous": {
                "category": "Hazardous",
                "message": "Health emergency: entire population is at risk.",
                "recommendation": "Emergency protection required. Avoid all outdoor activities. Multiple air purifiers recommended. N99 masks essential. Seek medical attention if experiencing symptoms.",
                "color": "maroon",
            },
        }
        
        return messages.get(category, messages["good"])
    
    def get_statistics(self, aqi: int) -> Dict[str, any]:
        """
        Get statistics about available products for given AQI.
        
        Args:
            aqi: Current AQI value
            
        Returns:
            Dictionary with product counts by category
        """
        category = self.get_aqi_category(aqi)
        
        stats = {
            "aqi": aqi,
            "category": category,
            "total_products": 0,
            "by_type": {},
            "priority_types": self.PRODUCT_PRIORITIES.get(category, []),
        }
        
        # Count products in range
        products = Product.objects.filter(
            aqi_min__lte=aqi,
            aqi_max__gte=aqi
        )
        
        stats["total_products"] = products.count()
        
        # Count by type
        for ptype in ["mask", "purifier", "room_purifier", "monitor", "car-filter", "plant"]:
            count = products.filter(product_type=ptype).count()
            stats["by_type"][ptype] = count
        
        return stats


# Convenience functions for direct import
def get_recommendations(aqi: int, category: Optional[str] = None, max_results: int = 50) -> List[Product]:
    """
    Convenience function to get recommendations without instantiating class.
    
    Usage:
        from aqi_app.utils.product_recommender import get_recommendations
        products = get_recommendations(aqi=150)
    """
    recommender = ProductRecommender()
    return recommender.get_recommendations(aqi, category, max_results)


def get_recommendation_message(aqi: int) -> Dict[str, str]:
    """
    Get recommendation message for AQI level.
    
    Usage:
        from aqi_app.utils.product_recommender import get_recommendation_message
        message = get_recommendation_message(aqi=150)
    """
    recommender = ProductRecommender()
    return recommender.get_recommendation_message(aqi)


def get_aqi_category(aqi: int) -> str:
    """
    Get AQI category name.
    
    Usage:
        from aqi_app.utils.product_recommender import get_aqi_category
        category = get_aqi_category(150)  # Returns "unhealthy_sensitive"
    """
    recommender = ProductRecommender()
    return recommender.get_aqi_category(aqi)