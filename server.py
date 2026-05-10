from fastmcp import FastMCP
import httpx

mcp = FastMCP("Weather MCP Server")


async def get_coordinates(city: str) -> dict:
    """Geocoding using Open-Meteo's free geocoding API."""
    url = "https://geocoding-api.open-meteo.com/v1/search"
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params={"name": city, "count": 1, "language": "es"})
        data = response.json()
        if not data.get("results"):
            return None
        result = data["results"][0]
        return {
            "name": result["name"],
            "country": result.get("country", ""),
            "latitude": result["latitude"],
            "longitude": result["longitude"],
        }


@mcp.tool(description="Obtiene el tiempo actual para una ciudad. Devuelve temperatura, sensación térmica, humedad, viento y descripción del estado del cielo.")
async def get_current_weather(city: str) -> str:
    """Consulta el tiempo actual de cualquier ciudad del mundo."""
    coords = await get_coordinates(city)
    if not coords:
        return f"No se encontró la ciudad: {city}"

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": coords["latitude"],
        "longitude": coords["longitude"],
        "current": [
            "temperature_2m",
            "apparent_temperature",
            "relative_humidity_2m",
            "wind_speed_10m",
            "weather_code",
            "precipitation",
        ],
        "wind_speed_unit": "kmh",
        "timezone": "auto",
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        data = response.json()

    current = data["current"]

    wmo_descriptions = {
        0: "Despejado", 1: "Mayormente despejado", 2: "Parcialmente nublado", 3: "Nublado",
        45: "Niebla", 48: "Niebla helada",
        51: "Llovizna ligera", 53: "Llovizna moderada", 55: "Llovizna intensa",
        61: "Lluvia ligera", 63: "Lluvia moderada", 65: "Lluvia intensa",
        71: "Nieve ligera", 73: "Nieve moderada", 75: "Nieve intensa",
        80: "Chubascos ligeros", 81: "Chubascos moderados", 82: "Chubascos intensos",
        95: "Tormenta", 96: "Tormenta con granizo", 99: "Tormenta con granizo intenso",
    }

    weather_desc = wmo_descriptions.get(current["weather_code"], f"Código {current['weather_code']}")

    return (
        f"🌍 {coords['name']}, {coords['country']}\n"
        f"🌤️  Estado: {weather_desc}\n"
        f"🌡️  Temperatura: {current['temperature_2m']}°C (sensación {current['apparent_temperature']}°C)\n"
        f"💧 Humedad: {current['relative_humidity_2m']}%\n"
        f"💨 Viento: {current['wind_speed_10m']} km/h\n"
        f"🌧️  Precipitación: {current['precipitation']} mm"
    )


@mcp.tool(description="Obtiene la previsión del tiempo para los próximos días (hasta 7) para una ciudad.")
async def get_weather_forecast(city: str, days: int = 3) -> str:
    """Consulta la previsión meteorológica de una ciudad para los próximos días."""
    if days < 1 or days > 7:
        return "El número de días debe estar entre 1 y 7."

    coords = await get_coordinates(city)
    if not coords:
        return f"No se encontró la ciudad: {city}"

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": coords["latitude"],
        "longitude": coords["longitude"],
        "daily": [
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_sum",
            "weather_code",
            "wind_speed_10m_max",
        ],
        "forecast_days": days,
        "timezone": "auto",
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        data = response.json()

    daily = data["daily"]
    wmo_descriptions = {
        0: "☀️ Despejado", 1: "🌤️ Mayormente despejado", 2: "⛅ Parcialmente nublado", 3: "☁️ Nublado",
        45: "🌫️ Niebla", 48: "🌫️ Niebla helada",
        51: "🌦️ Llovizna ligera", 53: "🌦️ Llovizna", 55: "🌧️ Llovizna intensa",
        61: "🌧️ Lluvia ligera", 63: "🌧️ Lluvia", 65: "🌧️ Lluvia intensa",
        71: "🌨️ Nieve ligera", 73: "🌨️ Nieve", 75: "❄️ Nieve intensa",
        80: "🌦️ Chubascos", 81: "🌧️ Chubascos moderados", 82: "⛈️ Chubascos fuertes",
        95: "⛈️ Tormenta", 96: "⛈️ Tormenta con granizo", 99: "⛈️ Tormenta fuerte",
    }

    lines = [f"📅 Previsión para {coords['name']}, {coords['country']} ({days} días)\n"]
    for i in range(days):
        desc = wmo_descriptions.get(daily["weather_code"][i], "—")
        lines.append(
            f"{daily['time'][i]}  {desc}\n"
            f"   🌡️ {daily['temperature_2m_min'][i]}°C – {daily['temperature_2m_max'][i]}°C  "
            f"💨 {daily['wind_speed_10m_max'][i]} km/h  "
            f"🌧️ {daily['precipitation_sum'][i]} mm"
        )

    return "\n".join(lines)


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8000))
    mcp.run(transport="streamable-http", host="0.0.0.0", port=port)
