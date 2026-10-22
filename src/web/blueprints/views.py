from __future__ import annotations

from typing import Any

from flask import Blueprint, jsonify, redirect, render_template

from src.devices.wifi import get_available_networks, is_wifi_connected

views_bp = Blueprint("views", __name__)

PAGE_ROUTES = (
    "/", "/index", "/scale", "/anpr", "/cloud",
    "/wifi", "/telemetry", "/errors", "/config", "/admin",
)

for route in PAGE_ROUTES:
    views_bp.add_url_rule(
        route,
        endpoint=f"page_{route.strip('/') or 'home'}",
        view_func=lambda: render_template("index.html"),
    )


@views_bp.route("/wifi_portal")
def wifi_portal() -> str:
    return render_template("wifi.html")


@views_bp.route("/networks")
def root_networks() -> Any:
    return jsonify({"success": True, "networks": get_available_networks()}), 200


@views_bp.route("/hotspot-detect.html")
@views_bp.route("/generate_204")
@views_bp.route("/canonical.html")
@views_bp.route("/ncsi.txt")
@views_bp.route("/connecttest.txt")
def captive_portal_probe() -> Any:
    """Redirect OS captive portal probes directly to the Wi-Fi setup page."""
    if not is_wifi_connected():
        return redirect("/wifi", code=302)
    return "", 204
