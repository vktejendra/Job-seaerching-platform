// =============================
//  JobLens — Dashboard Logic
// =============================

// --- Session Guard ---
const session = JSON.parse(localStorage.getItem('joblens_session') || 'null');
const API = "http://127.0.0.1:5000/api";
if (!session) window.location.href = 'index.html';

// Populate user info in sidebar
document.getElementById('sidebarName').textContent  = session?.name  || 'User';
document.getElementById('sidebarRole').textContent  = session?.role  || 'Analyst';
document.getElementById('sidebarAvatar').textContent = (session?.name || 'U')[0].toUpperCase();

function logout() {
  localStorage.removeItem('joblens_session');
  window.location.href = 'index.html';
}

// ---- AUTOCOMPLETE DATA ----
const LOCATIONS = [
  'Sydney', 'Melbourne', 'London', 'New York', 'San Francisco',
  'Toronto', 'Berlin', 'Paris', 'Singapore', 'Dubai',
  'Austin', 'Chicago', 'Seattle', 'Tokyo', 'Amsterdam',
  'Mumbai', 'Bangalore', 'Remote', 'Manchester', 'Edinburgh'
];

const ROLES = [
  'Data Scientist', 'Software Developer', 'Machine Learning Engineer',
  'Data Analyst', 'Backend Developer', 'Frontend Developer',
  'Full Stack Developer', 'DevOps Engineer', 'Product Manager',
  'UI/UX Designer', 'Cloud Architect', 'Business Analyst',
  'NLP Engineer', 'Python Developer', 'Java Developer',
  'React Developer', 'AI Engineer', 'Data Engineer'
];

const CATEGORIES = [
  'IT Jobs', 'Engineering Jobs', 'Accounting & Finance Jobs',
  'Healthcare & Nursing Jobs', 'Teaching Jobs', 'Sales Jobs',
  'Marketing & PR Jobs', 'Legal Jobs', 'Charity & Voluntary Jobs',
  'Retail Jobs', 'HR & Recruitment Jobs', 'Scientific & QA Jobs'
];

// ---- AUTOCOMPLETE LOGIC ----
function autocomplete(inputId, listId, source) {
  const input = document.getElementById(inputId).value.toLowerCase();
  const list  = document.getElementById(listId);

  if (input.length < 1) { list.classList.remove('show'); return; }

  const matches = source.filter(s => s.toLowerCase().includes(input)).slice(0, 6);
  if (!matches.length) { list.classList.remove('show'); return; }

  list.innerHTML = matches.map(m =>
    `<div class="autocomplete-item" onclick="selectSuggestion('${inputId}', '${listId}', '${m}')">
      <i class="fas fa-search"></i> ${m}
    </div>`
  ).join('');
  list.classList.add('show');
}

function selectSuggestion(inputId, listId, value) {
  document.getElementById(inputId).value = value;
  document.getElementById(listId).classList.remove('show');
}

// Close dropdowns on outside click
document.addEventListener('click', e => {
  document.querySelectorAll('.autocomplete-list').forEach(l => {
    if (!l.contains(e.target)) l.classList.remove('show');
  });
});

// ---- GEOLOCATION ----
function detectLocation() {
  const el = document.getElementById('userLocation');
  const status = document.getElementById('locStatus');
  if (!navigator.geolocation) {
    el.textContent = 'Location N/A';
    status.style.background = '#ff6b6b';
    return;
  }
  navigator.geolocation.getCurrentPosition(
    pos => {
      const lat = pos.coords.latitude.toFixed(3);
      const lon = pos.coords.longitude.toFixed(3);
      // Reverse geocode via open API
      fetch(`https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lon}&format=json`)
        .then(r => r.json())
        .then(data => {
          const city = data.address?.city || data.address?.town || data.address?.village || '';
          const country = data.address?.country || '';
          el.textContent = city ? `${city}, ${country}` : `${lat}, ${lon}`;
          // Pre-fill search location
          if (city && !document.getElementById('searchLocation').value) {
            document.getElementById('searchLocation').value = city;
          }
          status.style.background = '#00c896';
        })
        .catch(() => { el.textContent = `${lat}, ${lon}`; });
    },
    () => {
      el.textContent = 'Location denied';
      status.style.background = '#ff6b6b';
    }
  );
}
function refreshLocation() { detectLocation(); }
detectLocation();


// ---- SEARCH LOGIC ----
async function runSearch() {

    const location =
        document.getElementById("searchLocation").value;

    const role =
        document.getElementById("searchRole").value;

    const category =
        document.getElementById("searchCategory").value;

    try {

        const response = await fetch(
            `http://127.0.0.1:5000/api/search?location=${encodeURIComponent(location)}&role=${encodeURIComponent(role)}&category=${encodeURIComponent(category)}`
        );

        const data = await response.json();
        updateChartsForSearch(data.jobs);

         console.log(data);

        document.getElementById("resultsCount").innerText =
            `${data.count} jobs found`;

        const grid =
            document.getElementById("resultsGrid");

        grid.innerHTML = "";

        data.jobs.forEach(job => {

            grid.innerHTML += `
                <div class="job-card">
                    <h3>${job.title}</h3>

                    <p>
                        <i class="fas fa-building"></i>
                        ${job.company}
                    </p>

                    <p>
                        <i class="fas fa-map-marker-alt"></i>
                        ${job.location_display}
                    </p>

                    <p>
                        Salary:
                        $${Math.round(job.salary_min).toLocaleString()}
                        -
                        $${Math.round(job.salary_max).toLocaleString()}
                    </p>

                    <a
                        href="${job.redirect_url}"
                        target="_blank"
                        class="job-link">
                        View Job
                    </a>
                </div>
            `;
        });

    }
    catch(err) {

        console.error(err);

        alert("Search failed");

    }

}

function renderResults(jobs) {

  const section =
    document.getElementById("resultsSection");

  const grid =
    document.getElementById("resultsGrid");

  const count =
    document.getElementById("resultsCount");

  section.classList.add("visible");

  count.textContent =
    `${jobs.length} results found`;

  if(!jobs.length){

    grid.innerHTML =
      "<p>No jobs found.</p>";

    return;
  }

  grid.innerHTML = jobs.map(job => `

    <div class="job-card">

      <div class="job-company">
        ${job.company}
      </div>

      <div class="job-title">
        ${job.title}
      </div>

      <div class="job-meta">
        📍 ${job.location_display}
      </div>

      <div class="job-meta">
        ${job.category_label}
      </div>

      <div class="job-salary">
        $${Math.round(job.salary_min)}
        -
        $${Math.round(job.salary_max)}
      </div>

      <a
        href="${job.redirect_url}"
        target="_blank"
        class="search-btn">

        Apply

      </a>

    </div>

  `).join("");

}

function renderAIInsight(
  jobs,
  location,
  role
){

  const text =
    document.getElementById("aiInsightText");

  if(!jobs.length){

    text.innerHTML =
      "No jobs found.";

    return;
  }

  const avgSalary =
    Math.round(

      jobs.reduce(
        (sum,j)=>
          sum +
          (
            (j.salary_min +
             j.salary_max) / 2
          ),
        0
      ) / jobs.length

    );

  text.innerHTML = `

    Found
    <strong>${jobs.length}</strong>
    jobs.

    Average salary:
    <strong>$${avgSalary}</strong>

    for
    <strong>${role || "all roles"}</strong>

    in
    <strong>${location || "all locations"}</strong>

  `;
}

// ---- CHARTS ----
let charts = {};

function initCharts() {
  const gridColor = 'rgba(255,255,255,0.05)';
  const fontColor = '#8b8ba7';

  // Category Chart
  charts.category = new Chart(document.getElementById('categoryChart'), {
    type: 'bar',
    data: {
      labels: [],
      datasets: [{
        label: 'Postings',
        data: [],
        backgroundColor: [
          'rgba(108,99,255,0.7)', 'rgba(0,229,255,0.7)', 'rgba(0,200,150,0.7)',
          'rgba(255,179,71,0.7)', 'rgba(255,107,107,0.7)', 'rgba(149,97,226,0.7)',
          'rgba(80,200,120,0.7)', 'rgba(255,160,86,0.7)'
        ],
        borderRadius: 6, borderSkipped: false,
      }]
    },
    options: { ...barOptions(gridColor, fontColor) }
  });

  // Salary Chart
  charts.salary = new Chart(document.getElementById('salaryChart'), {
    type: 'bar',
    data: {
      labels: [],
      datasets: [
        { label: 'Min Salary', data: [], backgroundColor: 'rgba(108,99,255,0.5)', borderRadius: 4 },
        { label: 'Max Salary', data: [], backgroundColor: 'rgba(0,229,255,0.5)', borderRadius: 4 },
      ]
    },
    options: { ...barOptions(gridColor, fontColor) }
  });

  // Trend Chart
  charts.trend = new Chart(document.getElementById('trendChart'), {
    type: 'line',
    data: {
      datasets: [{
        label: 'Postings',
        borderColor: 'rgba(108,99,255,1)',
        backgroundColor: 'rgba(108,99,255,0.12)',
        tension: 0.4, fill: true, pointRadius: 4,
        pointBackgroundColor: 'rgba(108,99,255,1)',
      }]
    },
    options: { ...lineOptions(gridColor, fontColor) }
  });

  // Contract Chart
  charts.contract = new Chart(document.getElementById('contractChart'), {
    type: 'doughnut',
    data: {
      labels: [],
      datasets: [{
        data: [],
        backgroundColor: [
          'rgba(108,99,255,0.8)', 'rgba(0,229,255,0.8)',
          'rgba(255,179,71,0.8)', 'rgba(0,200,150,0.8)', 'rgba(255,107,107,0.8)'
        ],
        borderColor: 'transparent', hoverOffset: 6
      }]
    },
    options: {
      plugins: { legend: { labels: { color: fontColor, font: { family: 'Space Grotesk', size: 12 } } } },
      cutout: '65%'
    }
  });
   // Skills Chart
charts.skills = new Chart(document.getElementById('skillsChart'), {
  type: 'bar',
  data: {
    labels: [],
    datasets: [{
      label: 'Top Skills',
      data: [],
      backgroundColor: 'rgba(0,229,255,0.65)',
      borderRadius: 5
    }]
  },
  options: {
    indexAxis: 'y',
    ...barOptions(gridColor, fontColor, false)
  }
});
}
async function loadSkillsChart() {

    const response =
        await fetch(`${API}/top-skills`);

    const data =
        await response.json();

     console.log(data);

    charts.skills.data.labels =
        data.map(x => x.skill);

    charts.skills.data.datasets[0].data =
        data.map(x => x.count);

    charts.skills.update();
}
async function loadStats() {

    const response = await fetch(
        "http://127.0.0.1:5000/api/eda/stats"
    );

    const data = await response.json();

    document.getElementById("statTotal").innerText =
        data.total_postings.toLocaleString();

    document.getElementById("statCompanies").innerText =
        data.unique_companies.toLocaleString();

    const avgSalary =
        Math.round(
            (data.avg_salary_min + data.avg_salary_max) / 2
        );

    document.getElementById("statAvgSalary").innerText =
        "$" + avgSalary.toLocaleString();
}
async function loadCategoryChart() {

    const response = await fetch(`${API}/eda/stats`);
    const data = await response.json();

    console.log("Category Data:", data);

    const categories = data.top_categories;

    charts.category.data.labels =
        Object.keys(categories);

    charts.category.data.datasets[0].data =
        Object.values(categories);

    charts.category.update();
}
async function loadContractChart() {

    const response = await fetch(`${API}/eda/stats`);
    const data = await response.json();

    console.log("Contract Data:", data);

    const contracts =
        data.contract_time_dist;

    charts.contract.data.labels =
        Object.keys(contracts);

    charts.contract.data.datasets[0].data =
        Object.values(contracts);

    charts.contract.update();
}
async function loadTrendChart() {

    const response =
        await fetch(`${API}/trends`);

    const data =
        await response.json();

         console.log(data);

    charts.trend.data.labels =
        data.map(x => x.month);

    charts.trend.data.datasets[0].data =
        data.map(x => x.count);

    charts.trend.update();

}

function barOptions(gridColor, fontColor, legend = true) {
  return {
    responsive: true,
    plugins: {
      legend: { display: legend, labels: { color: fontColor, font: { family: 'Space Grotesk', size: 12 } } }
    },
    scales: {
      x: { grid: { color: gridColor }, ticks: { color: fontColor, font: { family: 'DM Mono', size: 11 } } },
      y: { grid: { color: gridColor }, ticks: { color: fontColor, font: { family: 'DM Mono', size: 11 } } }
    }
  };
}

function lineOptions(gridColor, fontColor) {
  return {
    responsive: true,
    plugins: { legend: { display: false } },
    scales: {
      x: { grid: { color: gridColor }, ticks: { color: fontColor, font: { family: 'DM Mono', size: 11 } } },
      y: { grid: { color: gridColor }, ticks: { color: fontColor, font: { family: 'DM Mono', size: 11 } } }
    }
  };
}

function updateChartsForSearch(jobs) {
  if (!jobs.length) return;
  // Update salary chart with search results
  const minSalary = jobs.map(j => j.salary_min / 1000);
  const maxSalary = jobs.map(j => j.salary_max / 1000);
  const labels    = jobs.map(j => j.title.split(' ').slice(0, 2).join(' '));

  charts.salary.data.labels = labels;
  charts.salary.data.datasets[0].data = minSalary;
  charts.salary.data.datasets[1].data = maxSalary;
  charts.salary.update();
}

// ---- GEO MAP (Leaflet) ----
let geoMap;

function initGeoMap() {

    geoMap = L.map('geoMap')
        .setView([20,0],2);

    L.tileLayer(
      'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
      {
          attribution:'© CARTO'
      }
    ).addTo(geoMap);

    loadGeoData();
}

async function loadGeoData() {

    const res = await fetch(`${API}/geo`);
    const data = await res.json();

console.log("Geo Data:", data);
console.log("Geo Count:", data.length);

    const heatData =
        data.map(item => [

            item.latitude,
            item.longitude,
            0.7

        ]);

    if(typeof L.heatLayer !== "undefined"){

        L.heatLayer(
            heatData,
            {
                radius:35,
                blur:25
            }
        ).addTo(geoMap);

    }
}

// ---- SPINNER ----
function showSpinner(text) {
  document.getElementById('spinnerOverlay').classList.add('show');
  document.getElementById('spinnerText').textContent = text || 'Processing...';
}
function hideSpinner() {
  document.getElementById('spinnerOverlay').classList.remove('show');
}

// ---- SIDEBAR NAV ----
function showSection(name, element) {

    // Sidebar active state
    document.querySelectorAll('.nav-item')
        .forEach(n => n.classList.remove('active'));

    element.classList.add('active');

    // Hide all sections
    document.querySelectorAll('.page-section')
        .forEach(section =>
            section.classList.remove('active-section')
        );

    // Show selected section
    const targetSection =
        document.getElementById(`section-${name}`);

    if (targetSection) {
        targetSection.classList.add('active-section');
    }

    // Update top bar title
    document.querySelector('.topbar-title span').textContent = ({
        dashboard: 'Global Job Market Intelligence',
        explore: 'Browse All 17,350 Postings',
        salary: 'ML-Powered Salary Predictor',
        skills: 'NLP Skill Extraction Engine',
        trends: 'Hiring Demand Over Time',
        geo: 'Geographic Intelligence',
        forecast: 'AI Hiring Forecast',
        classify: 'Job Category Classifier'
    })[name] || '';

    // Fix Leaflet map rendering when section becomes visible
    if (name === "geo" && typeof geoMap !== "undefined") {

        setTimeout(() => {

            geoMap.invalidateSize();

        }, 300);

    }
}
async function loadForecast() {

    const response =
        await fetch(`${API}/forecast`);

    const data =
        await response.json();

    console.log(data);

}
async function extractSkillsFromText(){

  const text =
    document.getElementById(
      "skillText"
    ).value;

  const response =
    await fetch(
      `${API}/extract-skills`,
      {
        method:"POST",
        headers:{
          "Content-Type":
          "application/json"
        },
        body:JSON.stringify({
          text:text
        })
      }
    );

  const data =
    await response.json();

  const result =
    document.getElementById(
      "skillsResult"
    );

  result.style.display =
    "block";

  result.innerHTML =

    data.skills.map(skill =>

      `<span class="skill-tag-large">${skill}</span>`

    ).join("");

}
document.addEventListener("DOMContentLoaded", async () => {

    document
      .getElementById("section-dashboard")
      .classList.add("active-section");

    initCharts();

    try {
        await loadCategoryChart();
        await loadStats();
        await loadContractChart();
        await loadTrendChart();
        await loadSkillsChart();
    }
    catch(error){
        console.error("Dashboard API loading failed:",
          error
        );
    }

    setTimeout(initGeoMap, 300);
});