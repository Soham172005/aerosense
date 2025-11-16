// ------------ TAB SWITCHING ------------
const tabs = document.querySelectorAll(".tab");
const contents = document.querySelectorAll(".tab-content");

tabs.forEach(tab => {
    tab.addEventListener("click", () => {
        tabs.forEach(t => t.classList.remove("active"));
        contents.forEach(c => c.classList.remove("active"));

        tab.classList.add("active");
        const id = tab.getAttribute("data-tab");
        document.getElementById(id).classList.add("active");
    });
});

// ------------ SIMULATION: Generate Trend Data ------------
function generateTrendData(base, days) {
    const arr = [];
    for (let i = days; i >= 0; i--) {
        const d = new Date();
        d.setDate(d.getDate() - i);

        const variation = Math.random() * 40 - 20;
        const aqi = Math.max(10, Math.min(300, base + variation));

        arr.push({
            date: d.toLocaleDateString(),
            aqi: Math.round(aqi),
            trend: Math.random() > 0.5 ? "up" : "down"
        });
    }
    return arr;
}

// ------------ FILL UI WITH DATA ------------
function updateTrends() {
    const time = parseInt(document.getElementById("time-range").value);
    const timelineContainer = document.getElementById("timeline-data");

    const trendData = generateTrendData(120, time);

    // Fill timeline
    timelineContainer.innerHTML = trendData.slice(-10).map(item => `
        <div class="timeline-item">
            <div>
                <div class="timeline-date">${item.date}</div>
                <div class="timeline-aqi">${item.aqi}</div>
            </div>
            <div>${item.trend === "up" ? "📈" : "📉"}</div>
        </div>
    `).join("");

    // Stats
    const values = trendData.map(i => i.aqi);
    const avg = Math.round(values.reduce((a,b)=>a+b,0) / values.length);
    const max = Math.max(...values);
    const min = Math.min(...values);

    document.getElementById("avg-aqi").innerText = avg;
    document.getElementById("max-aqi").innerText = max;
    document.getElementById("min-aqi").innerText = min;

    // Trend logic
    const recent = values.slice(-3);
    const earlier = values.slice(0,3);
    const recentAvg = recent.reduce((a,b)=>a+b,0)/3;
    const earlierAvg = earlier.reduce((a,b)=>a+b,0)/3;

    let trend = "stable";
    if (recentAvg > earlierAvg + 5) trend = "increasing";
    if (recentAvg < earlierAvg - 5) trend = "decreasing";

    document.getElementById("trend-text").innerText = trend;

    document.getElementById("trend-icon").innerText =
        trend === "increasing" ? "📈" :
        trend === "decreasing" ? "📉" : "📊";

    document.getElementById("trend-analysis-text").innerText =
        trend === "increasing"
        ? "Air quality is worsening in this period."
        : trend === "decreasing"
        ? "Air quality is improving in this period."
        : "Air quality remains relatively stable.";

    // Weekly / hourly
    const weekly = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"];
    document.getElementById("weekly-patterns").innerHTML =
        weekly.map(day => `
            <div class="pattern-row">
                ${day} — ${Math.round(avg + (Math.random()*20 - 10))}
            </div>
        `).join("");

    const hours = ["6 AM","9 AM","12 PM","3 PM","6 PM","9 PM"];
    document.getElementById("hourly-patterns").innerHTML =
        hours.map(h => `
            <div class="pattern-row">
                ${h} — ${Math.round(avg + (Math.random()*20 - 10))}
            </div>
        `).join("");
}

// Run initial load
updateTrends();

document.getElementById("city-select").addEventListener("change", updateTrends);
document.getElementById("time-range").addEventListener("change", updateTrends);
