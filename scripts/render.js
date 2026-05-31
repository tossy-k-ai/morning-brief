fetch("data/daily.json")
.then(response => response.json())
.then(data => {

document.getElementById("date").textContent = data.date;

document.getElementById("summary").innerHTML =
data.executive_summary
.map(item => `<li>${item}</li>`)
.join("");

const dashboard = document.getElementById("dashboard");

dashboard.innerHTML = Object.entries(data.dashboard)
.map(([key,value]) => `
<div class="metric">
<div class="metric-label">${key}</div>
<div class="metric-value">${value}</div>
</div>
`)
.join("");

function renderSection(id, section){

document.getElementById(id).innerHTML = `
<h3>${section.headline}</h3>

<p>${section.why}</p>

<div class="box">
<b>Watch:</b> ${section.watch}<br>
<b>Risk:</b> ${section.risk}<br>
<b>Implication:</b> ${section.implication}
</div>
`;
}

renderSection("rates", data.rates);
renderSection("fx", data.fx);
renderSection("commodities", data.commodities);

document.getElementById("macro").innerHTML = `
<h3>${data.macro_lesson.title}</h3>
<p>${data.macro_lesson.body}</p>
`;

document.getElementById("catalysts").innerHTML =
data.catalysts
.map(item => `<li>${item}</li>`)
.join("");

});