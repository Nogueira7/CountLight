# backend/app/main.py

from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from app.routes.recommendations import router as recommendations_router
from app.routes.alerts import router as alerts_router
from app.routes.reports import router as reports_router
from app.routes.plans import router as plans_router


from app.core.security import get_current_user
from app.db.database import get_db

# =====================================================
# ROUTERS
# =====================================================

from app.routes.auth import router as auth_router
from app.routes.houses import router as houses_router
from app.routes.rooms import router as rooms_router
from app.routes.devices import router as devices_router
from app.routes.user import router as users_router
from app.routes.energy import router as energy_router
from app.routes.dashboard import router as dashboard_router
from app.routes.achievement import router as achievement_router
from app.routes.goal import router as goal_router
from app.routes.notification import router as notification_router  # 🔔 NOVO
from app.routes import dev

# =====================================================
# REPOSITORIES (Dashboard Summary)
# =====================================================

from app.repositories.energy_repository import (
    get_energy_summary_by_room,
    get_energy_summary_by_device_type,
    get_energy_summary_by_device,
    get_total_consumption_for_period,
    get_estimated_month_cost,
    get_daily_consumption_in_month,
    get_hourly_consumption_today,
    get_daily_consumption_month_comparison,
)

# =====================================================
# APP
# =====================================================

app = FastAPI(
    title="CountLight",
    version="2.3.0"
)

# =====================================================
# STATIC FILES
# =====================================================

app.mount("/static", StaticFiles(directory="app/static"), name="static")

# =====================================================
# TEMPLATES
# =====================================================

templates = Jinja2Templates(directory="/root/CountLight/backend/app/templates")

# =====================================================
# CORS
# =====================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ⚠️ restringir em produção
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================================
# API ROUTERS
# =====================================================

app.include_router(auth_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(houses_router, prefix="/api")
app.include_router(rooms_router, prefix="/api")
app.include_router(devices_router, prefix="/api")
app.include_router(energy_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")
app.include_router(achievement_router, prefix="/api")
app.include_router(goal_router, prefix="/api")
app.include_router(notification_router, prefix="/api")
app.include_router(recommendations_router, prefix="/api")
app.include_router(alerts_router, prefix="/api")
app.include_router(reports_router, prefix="/api")
app.include_router(plans_router, prefix="/api")
app.include_router(dev.router, prefix="/api/dev", tags=["dev"])

# =====================================================
# DASHBOARD SUMMARY API
# =====================================================


@app.get("/api/dashboard/summary")
def dashboard_summary(
    user_id: int = Depends(get_current_user),
    db=Depends(get_db),
):
    summary_by_room = get_energy_summary_by_room(db, user_id)
    summary_by_type = get_energy_summary_by_device_type(db, user_id)
    summary_by_device = get_energy_summary_by_device(db, user_id)

    today_kwh = get_total_consumption_for_period(db, user_id, "today")
    month_kwh = get_total_consumption_for_period(db, user_id, "month")
    year_kwh = get_total_consumption_for_period(db, user_id, "year")
    month_cost = get_estimated_month_cost(db, user_id)

    daily_in_month = get_daily_consumption_in_month(db, user_id)
    consumption_by_hour = get_hourly_consumption_today(db, user_id)
    month_comparison = get_daily_consumption_month_comparison(db, user_id)

    return {
        "today_kwh": round(today_kwh, 2),
        "month_kwh": round(month_kwh, 2),
        "year_kwh": round(year_kwh, 2),
        "estimated_month_cost": month_cost,
        "summary_by_room": summary_by_room,
        "summary_by_type": summary_by_type,
        "summary_by_device": summary_by_device,
        "daily_in_month": daily_in_month["data"],
        "daily_in_month_has_data": daily_in_month["has_data"],
        "consumption_by_hour": consumption_by_hour["data"],
        "consumption_by_hour_has_data": consumption_by_hour["has_data"],
        "month_comparison": month_comparison,
    }


# =====================================================
# FRONTEND ROUTES (HTML)
# =====================================================


@app.get("/", response_class=HTMLResponse)
def root():
    return RedirectResponse(url="/dashboard")


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/login", response_class=HTMLResponse)
def login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/verify", response_class=HTMLResponse)
def verify_page(request: Request):
    return templates.TemplateResponse("verify.html", {"request": request})

@app.get("/reset-password", response_class=HTMLResponse)
def reset_password_page(request: Request):
    return templates.TemplateResponse("reset-password.html", {"request": request})

@app.get("/forgot-password", response_class=HTMLResponse)
def forgot_password_page(request: Request):
    return templates.TemplateResponse("forgot-password.html", {"request": request})

@app.get("/register", response_class=HTMLResponse)
def register(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@app.get("/pricing", response_class=HTMLResponse)
def pricing(request: Request):
    return templates.TemplateResponse("pricing.html", {"request": request})


@app.get("/alerts", response_class=HTMLResponse)
def alerts(request: Request):
    return templates.TemplateResponse("alerts.html", {"request": request})


@app.get("/simulation", response_class=HTMLResponse)
def simulation(request: Request):
    return templates.TemplateResponse("simulation.html", {"request": request})


@app.get("/houses", response_class=HTMLResponse)
def houses(request: Request):
    return templates.TemplateResponse("houses.html", {"request": request})


@app.get("/house-setup", response_class=HTMLResponse)
def house_setup(request: Request):
    return templates.TemplateResponse("house-setup.html", {"request": request})


@app.get("/statsroom/{id_room}", response_class=HTMLResponse)
def statsroom(request: Request, id_room: int):
    return templates.TemplateResponse(
        "statsroom.html",
        {
            "request": request,
            "id_room": id_room,
        },
    )


@app.get("/profile", response_class=HTMLResponse)
def profile(request: Request):
    return templates.TemplateResponse("profile.html", {"request": request})


# ✅ NOVO: perfil público (ou de outros utilizadores)
# Ex: http://127.0.0.1:8000/users/3
@app.get("/users/{user_id}", response_class=HTMLResponse)
def user_profile(request: Request, user_id: int):
    return templates.TemplateResponse(
        "user_profile.html",
        {
            "request": request,
            "user_id": user_id,
        },
    )


# ✅ NOVO: Profile Setup
@app.get("/profile_setup", response_class=HTMLResponse)
def profile_setup(request: Request):
    # certifica-te que existe: app/templates/profile_setup.html
    return templates.TemplateResponse("profile_setup.html", {"request": request})


@app.get("/settings", response_class=HTMLResponse)
def settings(request: Request):
    return templates.TemplateResponse("settings.html", {"request": request})


@app.get("/achievements", response_class=HTMLResponse)
def achievements_page(request: Request):
    return templates.TemplateResponse("achievements.html", {"request": request})


@app.get("/goal-setup", response_class=HTMLResponse)
def goal_setup_page(request: Request):
    return templates.TemplateResponse("goal-setup.html", {"request": request})

@app.get("/reports", response_class=HTMLResponse)
def reports_page(request: Request):
    return templates.TemplateResponse("reports.html", {"request": request})


# =====================================================
# HEALTH CHECK
# =====================================================


@app.get("/health")
def health():
    return {"status": "ok"}

