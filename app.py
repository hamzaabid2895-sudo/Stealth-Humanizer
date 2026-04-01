from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
from humanizer import UltimateHumanizer
import os

app = FastAPI(title="Stealth Humanizer Studio")

# Create templates directory if it doesn't exist
# Smart template loader (looks in 'templates' folder AND root directory for safety)
templates = Jinja2Templates(directory=["templates", "."])

# Initialize Humanizer globally to share connections
humanizer_engine = UltimateHumanizer()

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        request=request, 
        name="index.html", 
        context={"result": None, "original_text": ""}
    )

@app.get("/health")
async def health():
    import aiohttp
    results = {}
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get("https://www.google.com", timeout=5) as r:
                results["google"] = "reachable" if r.status == 200 else f"status {r.status}"
        except Exception as e:
            results["google"] = f"failed: {str(e)}"
            
        try:
            async with session.get("https://api.groq.com", timeout=5) as r:
                results["groq_api"] = "reachable" if r.status == 200 else f"status {r.status}"
        except Exception as e:
            results["groq_api"] = f"failed: {str(e)}"
            
    return {"status": "alive", "network_test": results}

@app.post("/humanize", response_class=HTMLResponse)
async def humanize_text(
    request: Request, 
    raw_text: str = Form(...),
    keywords: str = Form(None)
):
    kw_list = [k.strip() for k in keywords.split(",")] if keywords and keywords.strip() else []
    
    # Process the text using the Ultimate Humanizer!
    try:
        results = await humanizer_engine.humanize(raw_text, kw_list)
        final_output = results.get("final", "An error occurred during humanization.")
    except Exception as e:
        final_output = f"Error processing text: {str(e)}"
    
    return templates.TemplateResponse(
        request=request,
        name="index.html", 
        context={
            "result": final_output, 
            "original_text": raw_text,
            "keywords": keywords,
            "success": True if not final_output.startswith("Error") else False
        }
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"[*] Starting Stealth Web Server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
