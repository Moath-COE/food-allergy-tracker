from functools import lru_cache

from food_allergy_tracker.services.items import ItemService


@lru_cache
def get_item_service() -> ItemService:
    return ItemService()