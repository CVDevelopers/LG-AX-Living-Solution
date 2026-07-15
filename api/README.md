# api (Vercel entrypoint)

Thin shim exposing the FastAPI app as a Vercel Python serverless function (profile W, SPEC §12.1). All application code lives in `backend/` — this directory only exists because Vercel's convention requires functions under a root `api/`.

Vercel 서버리스 진입점. 애플리케이션 코드는 전부 `backend/`에 있으며, 이 디렉터리는 Vercel의 `api/` 규약 때문에 존재한다.
