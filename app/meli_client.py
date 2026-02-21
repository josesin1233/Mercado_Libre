import httpx
import logging
from app.config import settings

logger = logging.getLogger(__name__)


class MeliClient:
    BASE_URL = "https://api.mercadolibre.com"

    def __init__(self):
        self.token = settings.ACCESS_TOKEN

    def _headers(self):
        return {"Authorization": f"Bearer {self.token}"}

    async def _get(self, client: httpx.AsyncClient, url: str, **kwargs) -> httpx.Response:
        """GET con retry automático si el token expiró (401)."""
        r = await client.get(url, headers=self._headers(), **kwargs)
        if r.status_code == 401 and settings.REFRESH_TOKEN:
            await self.refresh_access_token()
            r = await client.get(url, headers=self._headers(), **kwargs)
        return r

    async def get_order(self, order_id: str) -> dict:
        async with httpx.AsyncClient() as client:
            r = await self._get(client, f"{self.BASE_URL}/orders/{order_id}")
            r.raise_for_status()
            return r.json()

    async def get_shipment(self, shipment_id: str) -> dict:
        async with httpx.AsyncClient() as client:
            r = await self._get(client, f"{self.BASE_URL}/shipments/{shipment_id}")
            r.raise_for_status()
            return r.json()

    async def get_order_items(self, order_id: str) -> list:
        order = await self.get_order(order_id)
        return order.get("order_items", [])

    async def get_recent_orders(self, limit: int = 50) -> dict:
        """Busca órdenes recientes del vendedor sin filtrar por status."""
        params = {
            "seller": settings.USER_ID,
            "sort": "date_desc",
            "limit": limit,
        }
        async with httpx.AsyncClient() as client:
            r = await self._get(client, f"{self.BASE_URL}/orders/search", params=params)
            if not r.is_success:
                body = ""
                try:
                    body = r.json()
                except Exception:
                    body = r.text
                raise httpx.HTTPStatusError(
                    f"ML API {r.status_code}: {body}",
                    request=r.request,
                    response=r,
                )
            return r.json()

    async def get_items_thumbnails(self, item_ids: list[str]) -> dict[str, str]:
        """Obtiene thumbnails de múltiples items en grupos de 20."""
        if not item_ids:
            return {}
        thumbnails = {}
        async with httpx.AsyncClient() as client:
            for i in range(0, len(item_ids), 20):
                batch = item_ids[i:i + 20]
                try:
                    r = await self._get(
                        client,
                        f"{self.BASE_URL}/items",
                        params={"ids": ",".join(batch)},
                    )
                    if r.status_code == 200:
                        for entry in r.json():
                            if entry.get("code") == 200:
                                body = entry.get("body", {})
                                thumbnails[str(body.get("id", ""))] = body.get("thumbnail", "")
                except Exception as exc:
                    logger.warning("Error al obtener thumbnails batch %s: %s", batch, exc)
        return thumbnails

    async def get_label_pdf(self, shipment_id: str) -> bytes | None:
        """Obtiene la etiqueta de envío en PDF desde la API de ML."""
        async with httpx.AsyncClient() as client:
            r = await self._get(
                client,
                f"{self.BASE_URL}/shipments/{shipment_id}/labels",
                params={"response_type": "pdf", "shipment_ids": shipment_id},
            )
            if r.status_code == 200:
                return r.content
        return None

    async def get_pending_shipments(self) -> list[dict]:
        """Obtiene las 100 órdenes más recientes pagadas."""
        data = await self.get_recent_orders(limit=50)
        orders = data.get("results", [])

        enriched = []
        all_item_ids = []

        async with httpx.AsyncClient() as client:
            for order in orders:
                shipping_id = order.get("shipping", {}).get("id")
                shipment_info = None
                if shipping_id:
                    try:
                        r = await self._get(client, f"{self.BASE_URL}/shipments/{shipping_id}")
                        if r.status_code == 200:
                            shipment_info = r.json()
                        else:
                            logger.warning("Shipment %s devolvió %s", shipping_id, r.status_code)
                    except Exception as exc:
                        logger.warning("Error al obtener shipment %s: %s", shipping_id, exc)

                for oi in order.get("order_items", []):
                    item_id = str(oi.get("item", {}).get("id", ""))
                    if item_id:
                        all_item_ids.append(item_id)

                enriched.append({
                    "order": order,
                    "shipment": shipment_info,
                    "shipment_id": shipping_id,
                })

        # Fetch thumbnails en batch y adjuntarlos
        thumbnails = await self.get_items_thumbnails(list(set(all_item_ids)))
        for entry in enriched:
            for oi in entry["order"].get("order_items", []):
                item_obj = oi.get("item")
                if isinstance(item_obj, dict):
                    item_id = str(item_obj.get("id", ""))
                    item_obj["thumbnail"] = thumbnails.get(item_id, "")

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
            settings.ACCESS_TOKEN = tokens["access_token"]
            settings.REFRESH_TOKEN = tokens["refresh_token"]
            self.token = tokens["access_token"]
            return tokens


meli = MeliClient()
