
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

app = FastAPI(
    title="GPR Media Intelligence",
    description="Local Media Monitoring and News Archive",
    version="0.1.0"
)

templates = Jinja2Templates(directory="app/templates")


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "app_name": "GPR Media Intelligence",
            "version": "0.1.0"
        }
    )


@app.get("/health")
async def health_check():
    return {
        "status": "running",
        "application": "GPR Media Intelligence"
    }
