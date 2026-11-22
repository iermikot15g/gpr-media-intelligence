
from urllib.parse import urlparse
import json

from datetime import date, datetime, time
from app.collector import collect_articles

from fastapi import FastAPI, Form, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from sqlalchemy import or_, func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database import Base, engine, get_db
from app.models import MediaSource, NewsArticle, SourceValidationRun
from app.source_validation import normalize_base_url, validate_source


app = FastAPI(
    title="GPR Media Intelligence",
    description="Local Media Monitoring and News Archive",
    version="0.2.0"
)

templates = Jinja2Templates(directory="app/templates")


# Membuat tabel database jika belum tersedia
Base.metadata.create_all(bind=engine)


def normalize_url(url: str) -> str:
    return normalize_base_url(url)


def seed_default_sources():
    """Memasukkan sumber awal hanya jika belum ada."""
    db = next(get_db())

    default_sources = [
        {
            "name": "Bongkar86",
            "base_url": "https://bongkar86.com",
            "description": "Custom Media Source"
        },
        {
            "name": "Ketikan",
            "base_url": "https://ketikan.com",
            "description": "Custom Media Source"
        },
        {
            "name": "Klik Madura",
            "base_url": "https://klikmadura.com",
            "description": "Custom Media Source"
        },
        {
            "name": "MEMO Online",
            "base_url": "https://www.memoonline.co.id",
            "description": "Media Online - Uji Coba Integrasi",
            "is_active": False,
        },
    ]

    try:
        for source in default_sources:
            existing = (
                db.query(MediaSource)
                .filter_by(base_url=source["base_url"])
                .first()
            )

            if not existing:
                db.add(MediaSource(**source))

        db.commit()
    finally:
        db.close()


seed_default_sources()


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return RedirectResponse(url="/sources", status_code=303)


@app.get("/sources", response_class=HTMLResponse)
async def source_list(
    request: Request,
    db: Session = Depends(get_db)
):
    sources = (
        db.query(MediaSource)
        .order_by(MediaSource.name.asc())
        .all()
    )

    total_sources = len(sources)
    active_sources = sum(1 for s in sources if s.is_active)
    inactive_sources = total_sources - active_sources
    validation_summaries = {}
    for item in sources:
        try:
            saved_report = json.loads(item.validation_report or "{}")
            validation_summaries[item.id] = saved_report.get("summary")
        except (TypeError, ValueError):
            validation_summaries[item.id] = None

    return templates.TemplateResponse(
        request=request,
        name="sources.html",
        context={
            "sources": sources,
            "total_sources": total_sources,
            "active_sources": active_sources,
            "inactive_sources": inactive_sources,
            "validation_summaries": validation_summaries,
            "message": request.query_params.get("message"),
            "error": request.query_params.get("error"),
            "edit_source": None
        }
    )


@app.post("/sources/add")
async def add_source(
    name: str = Form(...),
    base_url: str = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db)
):
    try:
        clean_url = normalize_url(base_url)

        source = MediaSource(
            name=name.strip(),
            base_url=clean_url,
            description=description.strip(),
            is_active=False
        )

        db.add(source)
        db.commit()

        return RedirectResponse(
            url="/sources?message=Sumber berhasil ditambahkan",
            status_code=303
        )

    except ValueError as error:
        db.rollback()
        return RedirectResponse(
            url=f"/sources?error={str(error)}",
            status_code=303
        )

    except IntegrityError:
        db.rollback()
        return RedirectResponse(
            url="/sources?error=Alamat website sudah terdaftar",
            status_code=303
        )


@app.get("/sources/{source_id}/edit", response_class=HTMLResponse)
async def edit_source_page(
    source_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    source = db.query(MediaSource).filter_by(id=source_id).first()

    if not source:
        return RedirectResponse(
            url="/sources?error=Sumber tidak ditemukan",
            status_code=303
        )

    sources = db.query(MediaSource).order_by(MediaSource.name.asc()).all()

    return templates.TemplateResponse(
        request=request,
        name="sources.html",
        context={
            "sources": sources,
            "total_sources": len(sources),
            "active_sources": sum(1 for s in sources if s.is_active),
            "inactive_sources": sum(1 for s in sources if not s.is_active),
            "validation_summaries": {
                item.id: (
                    json.loads(item.validation_report or "{}").get("summary")
                    if item.validation_report else None
                )
                for item in sources
            },
            "message": None,
            "error": None,
            "edit_source": source
        }
    )


@app.post("/sources/{source_id}/edit")
async def update_source(
    source_id: int,
    name: str = Form(...),
    base_url: str = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db)
):
    source = db.query(MediaSource).filter_by(id=source_id).first()

    if not source:
        return RedirectResponse(
            url="/sources?error=Sumber tidak ditemukan",
            status_code=303
        )

    try:
        new_base_url = normalize_url(base_url)
        changed_url = new_base_url.rstrip("/") != source.base_url.rstrip("/")

        source.name = name.strip()
        source.base_url = new_base_url
        source.description = description.strip()

        if changed_url:
            source.is_active = False
            source.validation_status = "not_tested"
            source.validated_at = None
            source.validation_config = None
            source.validation_report = None

        db.commit()

        return RedirectResponse(
            url="/sources?message=Sumber berhasil diperbarui",
            status_code=303
        )

    except ValueError as error:
        db.rollback()
        return RedirectResponse(
            url=f"/sources?error={str(error)}",
            status_code=303
        )

    except IntegrityError:
        db.rollback()
        return RedirectResponse(
            url="/sources?error=Alamat website sudah digunakan sumber lain",
            status_code=303
        )


@app.post("/sources/{source_id}/toggle")
async def toggle_source(
    source_id: int,
    db: Session = Depends(get_db)
):
    source = db.query(MediaSource).filter_by(id=source_id).first()

    if not source:
        return RedirectResponse(
            url="/sources?error=Sumber tidak ditemukan",
            status_code=303
        )

    if source.is_active:
        source.is_active = False
        message = "Sumber berhasil dinonaktifkan"
    else:
        if source.validation_status != "passed" or not source.validation_config:
            return RedirectResponse(
                url="/sources?error=Sumber harus lolos validasi teknis sebelum diaktifkan",
                status_code=303
            )
        source.is_active = True
        message = "Sumber berhasil diaktifkan"

    db.commit()

    return RedirectResponse(
        url=f"/sources?message={message}",
        status_code=303
    )


@app.post("/sources/{source_id}/validate")
def validate_source_route(
    source_id: int,
    db: Session = Depends(get_db)
):
    source = db.query(MediaSource).filter_by(id=source_id).first()
    if not source:
        return RedirectResponse(
            url="/sources?error=Sumber tidak ditemukan",
            status_code=303
        )

    # Revalidasi selalu menonaktifkan sumber selama pemeriksaan.
    source.is_active = False
    db.commit()

    report = validate_source(db, source)
    if report.get("overall_status") == "passed":
        return RedirectResponse(
            url="/sources?message=Validasi berhasil. Sumber menunggu persetujuan aktivasi",
            status_code=303
        )
    return RedirectResponse(
        url="/sources?error=Validasi belum berhasil. Periksa hasil pemeriksaan sumber",
        status_code=303
    )


@app.get("/sources/{source_id}/validation-history")
def source_validation_history(
    source_id: int,
    db: Session = Depends(get_db)
):
    source = db.query(MediaSource).filter_by(id=source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Sumber tidak ditemukan")
    runs = (
        db.query(SourceValidationRun)
        .filter(SourceValidationRun.source_id == source_id)
        .order_by(SourceValidationRun.started_at.desc())
        .limit(20)
        .all()
    )
    return {
        "source_id": source.id,
        "source_name": source.name,
        "validation_runs": [
            {
                "id": item.id,
                "started_at": item.started_at.isoformat() if item.started_at else None,
                "finished_at": item.finished_at.isoformat() if item.finished_at else None,
                "status": item.status,
                "report": json.loads(item.report) if item.report else None,
                "error_message": item.error_message,
            }
            for item in runs
        ],
    }


def _collection_page_context(db: Session, result=None, error=None,
                              date_from_value="", date_to_value="",
                              selected_source_ids=None):
    active_sources = (
        db.query(MediaSource)
        .filter(MediaSource.is_active.is_(True))
        .order_by(MediaSource.name.asc())
        .all()
    )
    # Default hanya memilih sumber aktif yang telah lolos validasi.
    # Sumber aktif lama tetap dapat dipilih manual tanpa mengubah statusnya.
    if selected_source_ids is None:
        selected_source_ids = [
            source.id for source in active_sources
            if source.validation_status == "passed" and source.validation_config
        ]
    return {
        "active_sources": active_sources,
        "selected_source_ids": selected_source_ids,
        "result": result,
        "error": error,
        "date_from_value": date_from_value,
        "date_to_value": date_to_value,
    }


@app.get("/collection")
def collection_page(
    request: Request,
    db: Session = Depends(get_db),
):
    context = _collection_page_context(db)
    context["request"] = request
    return templates.TemplateResponse(
        request=request,
        name="collection.html",
        context=context,
    )


@app.post("/collection/run")
def run_collection(
    request: Request,
    date_from: date = Form(...),
    date_to: date = Form(...),
    source_ids: list[int] = Form(default=[]),
    db: Session = Depends(get_db),
):
    selected_source_ids = list(dict.fromkeys(source_ids))
    if not selected_source_ids:
        context = _collection_page_context(
            db,
            error="Pilih minimal satu sumber media untuk menjalankan pengumpulan.",
            date_from_value=date_from.isoformat(),
            date_to_value=date_to.isoformat(),
            selected_source_ids=[],
        )
        context["request"] = request
        return templates.TemplateResponse(
            request=request, name="collection.html", context=context
        )

    if date_from > date_to:
        context = _collection_page_context(
            db,
            error="Tanggal awal tidak boleh melebihi tanggal akhir.",
            date_from_value=date_from.isoformat(),
            date_to_value=date_to.isoformat(),
            selected_source_ids=selected_source_ids,
        )
        context["request"] = request
        return templates.TemplateResponse(
            request=request, name="collection.html", context=context
        )

    # Hanya sumber aktif yang dipilih pengguna yang diproses.
    active_selected_ids = {
        source.id for source in db.query(MediaSource.id).filter(
            MediaSource.is_active.is_(True),
            MediaSource.id.in_(selected_source_ids),
        ).all()
    }
    if active_selected_ids != set(selected_source_ids):
        context = _collection_page_context(
            db,
            error="Pilihan sumber tidak valid atau ada sumber yang sudah tidak aktif. Muat ulang halaman.",
            date_from_value=date_from.isoformat(),
            date_to_value=date_to.isoformat(),
            selected_source_ids=sorted(active_selected_ids),
        )
        context["request"] = request
        return templates.TemplateResponse(
            request=request, name="collection.html", context=context
        )

    result = collect_articles(date_from, date_to, source_ids=selected_source_ids)
    context = _collection_page_context(
        db,
        result=result,
        date_from_value=date_from.isoformat(),
        date_to_value=date_to.isoformat(),
        selected_source_ids=selected_source_ids,
    )
    context["request"] = request
    return templates.TemplateResponse(
        request=request,
        name="collection.html",
        context=context,
    )

@app.get("/articles", response_class=HTMLResponse)
def article_archive(
    request: Request,
    q: str = "",
    source_id: str = "",
    date_from: str = "",
    date_to: str = "",
    sort: str = "newest",
    page: int = 1,
    db: Session = Depends(get_db),
):
    per_page = 20
    page = max(page, 1)
    sort = sort if sort in {"newest", "oldest"} else "newest"

    # Konversi filter media.
    selected_source = None
    if source_id.strip():
        try:
            selected_source = int(source_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="ID media tidak valid")

    # Konversi tanggal publikasi.
    parsed_date_from = None
    parsed_date_to = None
    try:
        if date_from.strip():
            parsed_date_from = date.fromisoformat(date_from)
        if date_to.strip():
            parsed_date_to = date.fromisoformat(date_to)
    except ValueError:
        raise HTTPException(status_code=400, detail="Format tanggal tidak valid")

    if parsed_date_from and parsed_date_to and parsed_date_from > parsed_date_to:
        raise HTTPException(
            status_code=400,
            detail="Tanggal awal tidak boleh melebihi tanggal akhir",
        )

    query = db.query(NewsArticle)

    # Pencarian mencakup judul dan isi artikel.
    if q.strip():
        keyword = f"%{q.strip()}%"
        query = query.filter(
            or_(
                NewsArticle.title.ilike(keyword),
                NewsArticle.content.ilike(keyword),
            )
        )

    if selected_source is not None:
        query = query.filter(NewsArticle.source_id == selected_source)

    if parsed_date_from:
        query = query.filter(
            NewsArticle.published_at >= datetime.combine(parsed_date_from, time.min)
        )
    if parsed_date_to:
        query = query.filter(
            NewsArticle.published_at <= datetime.combine(parsed_date_to, time.max)
        )

    total_articles = query.count()
    total_pages = max(1, (total_articles + per_page - 1) // per_page)
    page = min(page, total_pages)

    # Artikel tanpa tanggal publikasi ditempatkan setelah artikel bertanggal.
    if sort == "oldest":
        ordering = (
            NewsArticle.published_at.is_(None).asc(),
            NewsArticle.published_at.asc(),
            NewsArticle.id.asc(),
        )
    else:
        ordering = (
            NewsArticle.published_at.is_(None).asc(),
            NewsArticle.published_at.desc(),
            NewsArticle.id.desc(),
        )

    articles = (
        query.order_by(*ordering)
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    sources = db.query(MediaSource).order_by(MediaSource.name.asc()).all()
    total_articles_all = db.query(func.count(NewsArticle.id)).scalar() or 0
    total_sources = db.query(func.count(MediaSource.id)).scalar() or 0

    article_counts = (
        db.query(
            MediaSource.name,
            func.count(NewsArticle.id).label("article_count"),
        )
        .outerjoin(NewsArticle, NewsArticle.source_id == MediaSource.id)
        .group_by(MediaSource.id, MediaSource.name)
        .order_by(MediaSource.name.asc())
        .all()
    )

    return templates.TemplateResponse(
        request=request,
        name="articles.html",
        context={
            "articles": articles,
            "sources": sources,
            "q": q,
            "selected_source": selected_source,
            "date_from": parsed_date_from,
            "date_to": parsed_date_to,
            "sort": sort,
            "page": page,
            "total_pages": total_pages,
            "total_articles": total_articles,
            "total_articles_all": total_articles_all,
            "total_sources": total_sources,
            "article_counts": article_counts,
        },
    )


@app.get("/articles/{article_id}", response_class=HTMLResponse)
def article_detail(
    article_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    article = (
        db.query(NewsArticle)
        .filter(NewsArticle.id == article_id)
        .first()
    )

    if article is None:
        raise HTTPException(
            status_code=404,
            detail="Artikel tidak ditemukan",
        )

    return templates.TemplateResponse(
        request=request,
        name="article_detail.html",
        context={
            "article": article,
        },
    )

@app.get("/health")
async def health_check():
    return {
        "status": "running",
        "application": "GPR Media Intelligence",
        "version": "0.2.0"
    }
