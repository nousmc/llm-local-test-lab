import json
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ConfiguredModel, ProviderConfig
from ..services.provider_router import get_provider_client

router = APIRouter(prefix="/models", tags=["models"])


@router.get("/", response_class=HTMLResponse)
async def model_list(request: Request, db: Session = Depends(get_db)):
    models = db.query(ConfiguredModel).all()
    providers = db.query(ProviderConfig).all()
    return request.app.state.templates.TemplateResponse(
        request=request,
        name="model_list.html",
        context={"request": request, "models": models, "providers": providers, "mode": "list"},
    )


@router.get("/new", response_class=HTMLResponse)
async def model_new(request: Request, db: Session = Depends(get_db)):
    providers = db.query(ProviderConfig).all()
    return request.app.state.templates.TemplateResponse(
        request=request,
        name="model_list.html",
        context={"request": request, "model": None, "providers": providers, "mode": "create"},
    )


@router.post("/")
async def model_create(
    request: Request,
    model_id: str = Form(...),
    label: str = Form(...),
    provider: str = Form(...),
    model_name: str = Form(...),
    enabled: str = Form("true"),
    family: str = Form(""),
    size_b: str = Form(""),
    context_window: str = Form(""),
    supports_vision: str = Form("false"),
    supports_json: str = Form("false"),
    temperature: str = Form("0.0"),
    top_p: str = Form("0.9"),
    max_tokens: str = Form("1024"),
    db: Session = Depends(get_db),
):
    existing = db.query(ConfiguredModel).filter(ConfiguredModel.id == model_id).first()
    if existing:
        return RedirectResponse(url="/models", status_code=303)

    params = {"temperature": float(temperature), "top_p": float(top_p), "max_tokens": int(max_tokens)}

    model = ConfiguredModel(
        id=model_id,
        label=label,
        provider=provider,
        model_name=model_name,
        enabled=enabled == "true",
        family=family or None,
        size_b=int(size_b) if size_b else None,
        context_window=int(context_window) if context_window else None,
        supports_vision=supports_vision == "true",
        supports_json=supports_json == "true",
        default_params_json=json.dumps(params),
    )
    db.add(model)
    db.commit()
    return RedirectResponse(url="/models", status_code=303)


@router.get("/{model_id:path}/edit", response_class=HTMLResponse)
async def model_edit(model_id: str, request: Request, db: Session = Depends(get_db)):
    model = db.query(ConfiguredModel).filter(ConfiguredModel.id == model_id).first()
    if not model:
        return RedirectResponse(url="/models")
    providers = db.query(ProviderConfig).all()
    return request.app.state.templates.TemplateResponse(
        request=request,
        name="model_list.html",
        context={"request": request, "model": model, "providers": providers, "mode": "edit"},
    )


@router.post("/{model_id:path}/update")
async def model_update(
    model_id: str,
    request: Request,
    new_id: str = Form(...),
    label: str = Form(...),
    provider: str = Form(...),
    model_name: str = Form(...),
    enabled: str = Form("true"),
    family: str = Form(""),
    size_b: str = Form(""),
    context_window: str = Form(""),
    supports_vision: str = Form("false"),
    supports_json: str = Form("false"),
    temperature: str = Form("0.0"),
    top_p: str = Form("0.9"),
    max_tokens: str = Form("1024"),
    db: Session = Depends(get_db),
):
    model = db.query(ConfiguredModel).filter(ConfiguredModel.id == model_id).first()
    if not model:
        return RedirectResponse(url="/models")

    if new_id != model_id:
        existing = db.query(ConfiguredModel).filter(ConfiguredModel.id == new_id).first()
        if existing:
            return RedirectResponse(url="/models")

    params = {"temperature": float(temperature), "top_p": float(top_p), "max_tokens": int(max_tokens)}

    model.id = new_id
    model.label = label
    model.provider = provider
    model.model_name = model_name
    model.enabled = enabled == "true"
    model.family = family or None
    model.size_b = int(size_b) if size_b else None
    model.context_window = int(context_window) if context_window else None
    model.supports_vision = supports_vision == "true"
    model.supports_json = supports_json == "true"
    model.default_params_json = json.dumps(params)
    model.updated_at = datetime.now(timezone.utc)
    db.commit()
    return RedirectResponse(url="/models", status_code=303)


@router.post("/{model_id:path}/delete")
async def model_delete(model_id: str, db: Session = Depends(get_db)):
    model = db.query(ConfiguredModel).filter(ConfiguredModel.id == model_id).first()
    if model:
        db.delete(model)
        db.commit()
    return RedirectResponse(url="/models", status_code=303)


@router.post("/{model_id:path}/enable")
async def model_enable(model_id: str, db: Session = Depends(get_db)):
    model = db.query(ConfiguredModel).filter(ConfiguredModel.id == model_id).first()
    if model:
        model.enabled = True
        db.commit()
    return RedirectResponse(url="/models", status_code=303)


@router.post("/{model_id:path}/disable")
async def model_disable(model_id: str, db: Session = Depends(get_db)):
    model = db.query(ConfiguredModel).filter(ConfiguredModel.id == model_id).first()
    if model:
        model.enabled = False
        db.commit()
    return RedirectResponse(url="/models", status_code=303)


@router.post("/{model_id:path}/probe")
async def model_probe(model_id: str, db: Session = Depends(get_db)):
    model = db.query(ConfiguredModel).filter(ConfiguredModel.id == model_id).first()
    if not model:
        return {"success": False, "response": "", "latency_ms": 0, "error": "Model not found"}

    client = get_provider_client(model.provider)
    result = await client.probe(model.model_name)

    return {
        "success": result.get("error") is None,
        "response": result.get("text", ""),
        "latency_ms": result.get("timing", {}).get("latency_ms", 0),
        "error": result.get("error"),
    }
