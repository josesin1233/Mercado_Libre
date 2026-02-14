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

    async def get_recent_orders(self, status: str = "paid") -> dict:
        """Busca órdenes recientes del vendedor filtradas por status."""
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{self.BASE_URL}/orders/search",
                params={
                    "seller": settings.USER_ID,
                    "order.status": status,
                    "sort": "date_desc",
                    "limit": 50,
                },
                headers=self._headers(),
            )
            r.raise_for_status()
            return r.json()

    async def get_pending_shipments(self) -> list[dict]:
        """Obtiene órdenes pagadas y agrega info de envío para ver cuáles faltan por entregar."""
        data = await self.get_recent_orders("paid")
        orders = data.get("results", [])

        enriched = []
        async with httpx.AsyncClient() as client:
            for order in orders:
                shipping_id = order.get("shipping", {}).get("id")
                shipment_info = None
                if shipping_id:
                    try:
                        r = await client.get(
                            f"{self.BASE_URL}/shipments/{shipping_id}",
                            headers=self._headers(),
                        )
                        if r.status_code == 200:
                            shipment_info = r.json()
                    except Exception:
                        pass

                enriched.append({
                    "order": order,
                    "shipment": shipment_info,
                })

        return enriched

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
