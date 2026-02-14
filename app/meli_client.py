import httpx
from app.config import settings


class MeliClient:
    BASE_URL = "https://api.mercadolibre.com"

    def __init__(self):
        self.token = settings.ACCESS_TOKEN

    def _headers(self):
        return {"Authorization": f"Bearer {self.token}"}

    async def get_order(self, order_id: str) -> dict:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{self.BASE_URL}/orders/{order_id}",
                headers=self._headers(),
            )
            r.raise_for_status()
            return r.json()

    async def get_shipment(self, shipment_id: str) -> dict:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{self.BASE_URL}/shipments/{shipment_id}",
                headers=self._headers(),
            )
            r.raise_for_status()
            return r.json()

    async def get_order_items(self, order_id: str) -> list:
        order = await self.get_order(order_id)
        return order.get("order_items", [])

    async def refresh_access_token(self) -> dict:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{self.BASE_URL}/oauth/token",
                data={
                    "grant_type": "refresh_token",
                    "client_id": settings.APP_ID,
                    "client_secret": settings.CLIENT_SECRET,
                    "refresh_token": settings.REFRESH_TOKEN,
                },
            )
            r.raise_for_status()
            tokens = r.json()
            # Actualizar en memoria
            settings.ACCESS_TOKEN = tokens["access_token"]
            settings.REFRESH_TOKEN = tokens["refresh_token"]
            self.token = tokens["access_token"]
            return tokens


meli = MeliClient()
