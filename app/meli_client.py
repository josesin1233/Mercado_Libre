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

    async def get_recent_orders(self, limit: int = 51) -> dict:
        """Busca órdenes pagadas del vendedor con paginación (2 páginas = hasta 102 órdenes)."""
        all_results = []
        async with httpx.AsyncClient() as client:
            for offset in (0, limit):
                params = {
                    "seller": settings.USER_ID,
                    "order.status": "paid",
                    "sort": "date_desc",
                    "limit": limit,
                    "offset": offset,
                }
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
                data = r.json()
                results = data.get("results", [])
                all_results.extend(results)
                if len(results) < limit:
                    break
        return {"results": all_results}

    async def get_items_thumbnails(
        self,
        item_variation_pairs: list[tuple[str, str | None]],
    ) -> dict[tuple[str, str | None], str]:
        """
        Obtiene thumbnails para pares (item_id, variation_id).

        Cuando se provee variation_id, busca la foto específica de esa variante
        usando el campo variations[].picture_ids del listado. Si no encuentra
        foto de variante, cae de vuelta al thumbnail del listado principal.

        Retorna dict keyed por (item_id, variation_id) → URL del thumbnail.
        """
        if not item_variation_pairs:
            return {}

        unique_item_ids = list({p[0] for p in item_variation_pairs})
        # item_id → (thumbnail, {variation_id: picture_url})
        item_data: dict[str, tuple[str, dict[str, str]]] = {}

        async with httpx.AsyncClient() as client:
            for i in range(0, len(unique_item_ids), 20):
                batch = unique_item_ids[i:i + 20]
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
                                iid = str(body.get("id", ""))
                                main_thumb = body.get("thumbnail", "")
                                pictures: list[dict] = body.get("pictures", [])
                                # Construir mapa picture_id → url
                                pic_url: dict[str, str] = {
                                    p["id"]: p.get("url", p.get("secure_url", ""))
                                    for p in pictures
                                    if p.get("id")
                                }
                                # Variantes
                                var_thumbs: dict[str, str] = {}
                                for var in body.get("variations", []):
                                    vid = str(var.get("id", ""))
                                    if not vid:
                                        continue
                                    vpics = var.get("picture_ids", [])
                                    url = ""
                                    for vpid in vpics:
                                        url = pic_url.get(str(vpid), "")
                                        if url:
                                            break
                                    var_thumbs[vid] = url or main_thumb
                                item_data[iid] = (main_thumb, var_thumbs)
                except Exception as exc:
                    logger.warning("Error al obtener thumbnails batch %s: %s", batch, exc)

        result: dict[tuple[str, str | None], str] = {}
        for item_id, variation_id in item_variation_pairs:
            main_thumb, var_thumbs = item_data.get(item_id, ("", {}))
            if variation_id and variation_id in var_thumbs:
                result[(item_id, variation_id)] = var_thumbs[variation_id]
            else:
                result[(item_id, variation_id)] = main_thumb
        return result


    async def get_pending_shipments(self) -> list[dict]:
        """Obtiene las 100 órdenes más recientes pagadas."""
        data = await self.get_recent_orders(limit=50)
        orders = data.get("results", [])

        enriched = []
        all_pairs: list[tuple[str, str | None]] = []

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
                    variation_id = str(oi.get("item", {}).get("variation_id", "") or "")
                    if item_id:
                        pair = (item_id, variation_id or None)
                        if pair not in all_pairs:
                            all_pairs.append(pair)

                enriched.append({
                    "order": order,
                    "shipment": shipment_info,
                    "shipment_id": shipping_id,
                })

        # Fetch thumbnails en batch por (item_id, variation_id) y adjuntarlos
        thumbnails = await self.get_items_thumbnails(all_pairs)
        for entry in enriched:
            for oi in entry["order"].get("order_items", []):
                item_obj = oi.get("item")
                if isinstance(item_obj, dict):
                    item_id = str(item_obj.get("id", ""))
                    variation_id = str(item_obj.get("variation_id", "") or "") or None
                    item_obj["thumbnail"] = thumbnails.get((item_id, variation_id), "")

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
