from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
import uvicorn

from browser_automation import get_visual_match_html

app = FastAPI()

@app.get("/google-lens-visual", response_class=HTMLResponse)
def google_lens_visual(imageUrl: str = Query(...)):
    try:
        html = get_visual_match_html(imageUrl)
        return HTMLResponse(content=html, status_code=200)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001, workers=1)
