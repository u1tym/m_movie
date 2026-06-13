from fastapi import HTTPException, Request
import jwt


class JWTVerifier:
    def __init__(self, secret_key: str, algorithm: str, cookie_name: str) -> None:
        self._secret_key = secret_key
        self._algorithm = algorithm
        self._cookie_name = cookie_name

    def get_raw_token(self, request: Request) -> str | None:
        return request.cookies.get(self._cookie_name)

    def decode_token(self, token: str) -> dict[str, object]:
        try:
            payload: dict[str, object] = jwt.decode(
                token,
                self._secret_key,
                algorithms=[self._algorithm],
            )
            return payload
        except jwt.PyJWTError as exc:
            raise HTTPException(
                status_code=401,
                detail="認証トークンが無効です",
            ) from exc

    def verify_request(self, request: Request) -> dict[str, object]:
        token = self.get_raw_token(request)
        if token is None:
            raise HTTPException(status_code=401, detail="認証が必要です")
        return self.decode_token(token)

    def dependency(self):
        def _require_user(request: Request) -> dict[str, object]:
            return self.verify_request(request)

        return _require_user
