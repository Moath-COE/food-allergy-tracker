# routers/items.py
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from food_allergy_tracker.deps import get_item_service
from food_allergy_tracker.schemas.items import Item, ItemCreate
from food_allergy_tracker.services.items import ItemService

router = APIRouter(prefix="/items", tags=["items"])

ServiceDep = Annotated[ItemService, Depends(get_item_service)]


@router.get("")
def list_items(service: ServiceDep) -> list[Item]:
    return service.list()


@router.get("/{item_id}")
def get_item(item_id: int, service: ServiceDep) -> Item:
    item = service.get(item_id)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
    return item


@router.post("", status_code=status.HTTP_201_CREATED)
def create_item(data: ItemCreate, service: ServiceDep) -> Item:
    return service.create(data)