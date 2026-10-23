"""한국관광공사 국문 무장애여행 서비스(KorWithService2) 클라이언트."""
import json
import re
import urllib.parse

import requests

DEFAULT_BASE_URL = "https://apis.data.go.kr/B551011/KorWithService2"
QUOTA_EXCEEDED = "LIMITED_NUMBER_OF_SERVICE_REQUESTS_EXCEEDS_ERROR"


class TourApiError(Exception):
    pass


class TourApi:
    def __init__(self, service_key, base_url=DEFAULT_BASE_URL, session=None):
        # .env 에 인코딩된 키가 들어 있어도 requests 가 다시 인코딩하므로 한 번 풀어 둔다.
        self.service_key = urllib.parse.unquote(service_key)
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()

    def _get(self, operation, **params):
        query = {
            "serviceKey": self.service_key,
            "MobileOS": "ETC",
            "MobileApp": "BarrierFreeMap",
            "_type": "json",
        }
        query.update({k: v for k, v in params.items() if v not in (None, "")})
        try:
            res = self.session.get(f"{self.base_url}/{operation}", params=query, timeout=15)
        except requests.RequestException as e:
            # 예외 메시지에는 serviceKey 가 포함된 요청 URL 이 들어 있어 화면에 그대로 노출하면 안 된다.
            raise TourApiError(f"네트워크 오류 ({type(e).__name__})") from e

        body = res.text.lstrip()
        if body.startswith("<"):
            # 인증·한도 등 포털 오류는 _type=json 이어도 XML 로 온다.
            m = (re.search(r"<returnAuthMsg>(.*?)</returnAuthMsg>", body)
                 or re.search(r"<errMsg>(.*?)</errMsg>", body))
            raise TourApiError(m.group(1) if m else f"알 수 없는 오류 (HTTP {res.status_code})")
        try:
            data = json.loads(body)["response"]
        except (ValueError, KeyError, TypeError) as e:
            raise TourApiError(f"응답 해석 실패 (HTTP {res.status_code})") from e

        header = data.get("header", {})
        if header.get("resultCode") != "0000":
            raise TourApiError(header.get("resultMsg") or "알 수 없는 오류")

        result = data.get("body") or {}
        items = result.get("items")
        items = items.get("item", []) if isinstance(items, dict) else []
        if isinstance(items, dict):
            items = [items]
        return items, int(result.get("totalCount") or 0)

    def area_codes(self, area_code=None):
        items, _ = self._get("areaCode2", areaCode=area_code, numOfRows=100, pageNo=1)
        return [{"code": str(i["code"]), "name": i["name"]} for i in items]

    def search(self, area_code=None, sigungu_code=None, content_type_id=None, keyword=None):
        keyword = (keyword or "").strip() or None
        if not area_code:
            sigungu_code = None
        operation = "searchKeyword2" if keyword else "areaBasedList2"
        items, total = self._get(
            operation, keyword=keyword, areaCode=area_code, sigunguCode=sigungu_code,
            contentTypeId=content_type_id, numOfRows=100, pageNo=1, arrange="C",
        )
        places = []
        for item in items:
            try:
                x, y = float(item.get("mapx") or 0), float(item.get("mapy") or 0)
            except ValueError:
                continue
            if x and y:
                place = {**item, "mapx": x, "mapy": y}
                # https 배포 화면에서 혼합 콘텐츠로 막히지 않도록 이미지 주소를 https 로 바꾼다.
                for key in ("firstimage", "firstimage2"):
                    if str(place.get(key) or "").startswith("http://"):
                        place[key] = "https://" + place[key][len("http://"):]
                places.append(place)
        return places, total

    def area_based_page(self, area_code, page, rows=1000):
        """데이터셋 수집용: 좌표 필터 없이 지역 목록 한 페이지를 그대로 돌려준다."""
        return self._get("areaBasedList2", areaCode=area_code, numOfRows=rows, pageNo=page, arrange="C")

    def barrier_free(self, content_id):
        items, _ = self._get("detailWithTour2", contentId=content_id)
        if not items:
            return {}
        return {k: str(v).strip() for k, v in items[0].items()
                if k != "contentid" and str(v or "").strip()}
