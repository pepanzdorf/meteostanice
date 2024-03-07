let currentScript = document.currentScript;

function roundAndFormatNumber(number) {
    return parseFloat(parseFloat(number).toFixed(2)).toString();
}

function fetchCurrentWeather() {
    fetch("/api/v1/weather/last")
        .then(response => response.json())
        .then(data => updateView(data))
        .catch(err => showError(err));
}

function updateView(data) {
    let page_id = parseInt(currentScript.getAttribute("page_id"));
    if (page_id === 0) {
        if (data.rain !== null) {
            document.getElementById("rain_value").textContent = (data.rain * 0.08).toString();
        } else {
            document.getElementById("rain_value").textContent = "null";
        }
        if (data.pressure_bmp280 !== null) {
            document.getElementById("pressure_value").textContent = roundAndFormatNumber(data.pressure_bmp280 / 100);
        } else {
            document.getElementById("pressure_value").textContent = "null";
        }
        if (data.temperature_ds18b20 !== null) {
            document.getElementById("temperature_balcony_value").textContent = roundAndFormatNumber(data.temperature_ds18b20);
        } else {
            document.getElementById("temperature_balcony_value").textContent = "null";
        }
        if (data.temperature_bmp280 !== null) {
            document.getElementById("temperature_value").textContent = roundAndFormatNumber(data.temperature_bmp280);
        } else {
            document.getElementById("temperature_value").textContent = "null";
        }
        if (data.humidity_dht !== null) {
            document.getElementById("humidity_value").textContent = data.humidity_dht.toString();
        } else {
            document.getElementById("humidity_value").textContent = "null";
        }
        if (data.light_bh1750 !== null) {
            document.getElementById("lux_value").textContent = roundAndFormatNumber(data.light_bh1750);
        } else {
            document.getElementById("lux_value").textContent = "null";
        }
        document.getElementById("time").textContent = data.formatted_date;
    } else if (page_id === 1) { // rain
        if (data.rain !== null) {
            document.getElementById("value").textContent = (data.rain * 0.08).toString();
        } else {
            document.getElementById("value").textContent = "null";
        }
        document.getElementById("time").textContent = "Aktuálně(mm/5min)\n" + data.formatted_date;
    } else if (page_id === 2) { // pressure
        if (data.pressure_bmp280 !== null) {
            document.getElementById("value").textContent = roundAndFormatNumber(data.pressure_bmp280 / 100);
        } else {
            document.getElementById("value").textContent = "null";
        }
        document.getElementById("time").textContent = "Aktuálně(hPa)\n" + data.formatted_date;
    } else if (page_id === 3) { // temperature
        if (data.temperature_ds18b20 !== null) {
            document.getElementById("value").textContent = roundAndFormatNumber(data.temperature_ds18b20);
        } else {
            document.getElementById("value").textContent = "null";
        }
        document.getElementById("time").textContent = "Aktuálně(˚C)\n" + data.formatted_date;
    } else if (page_id === 4) { // humidity
        if (data.humidity_dht !== null) {
            document.getElementById("value").textContent = data.humidity_dht.toString();
        } else {
            document.getElementById("value").textContent = "null";
        }
        document.getElementById("time").textContent = "Aktuálně(%)\n" + data.formatted_date;
    }
}

function showError(err) {
    console.error(err);
    alert("Error fetching current weather data.");
}

setInterval(fetchCurrentWeather, 2.5 * 60 * 1000); // 2.5 minutes
