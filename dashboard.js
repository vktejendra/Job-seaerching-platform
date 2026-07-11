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
        renderResults(data.jobs);

renderAIInsight(
    data.jobs,
    location,
    role
);

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

// ---- ANALYTICS SECTIONS (Trends / Geo / Forecast) ----
// These three pages each have their own canvases/map div. Track load-state
// per section so we only build each Chart.js instance / Leaflet map once
// (re-creating a Chart on a canvas that already has one throws
// "Canvas is already in use").
const sectionsLoaded = { trends: false, geo: false, forecast: false };

async function loadTrendsSection() {
  if (sectionsLoaded.trends) return;
  sectionsLoaded.trends = true;

  const gridColor = 'rgba(255,255,255,0.05)';
  const fontColor = '#8b8ba7';

  try {
    // Postings by category
    const statsRes = await fetch(`${API}/eda/stats`);
    const stats = await statsRes.json();

    charts.trendsCategory = new Chart(document.getElementById('trendsChartCanvas'), {
      type: 'bar',
      data: {
        labels: Object.keys(stats.top_categories),
        datasets: [{
          label: 'Postings',
          data: Object.values(stats.top_categories),
          backgroundColor: 'rgba(108,99,255,0.7)',
          borderRadius: 6
        }]
      },
      options: barOptions(gridColor, fontColor, false)
    });

    // Average salary by category
    const salaryRes = await fetch(`${API}/salary-by-category`);
    const salaryData = await salaryRes.json();

    charts.trendsSalary = new Chart(document.getElementById('trendsSalaryCanvas'), {
      type: 'bar',
      data: {
        labels: salaryData.map(x => x.category),
        datasets: [{
          label: 'Avg Salary',
          data: salaryData.map(x => Math.round(x.avg_salary)),
          backgroundColor: 'rgba(0,229,255,0.7)',
          borderRadius: 6
        }]
      },
      options: barOptions(gridColor, fontColor, false)
    });
  } catch (err) {
    console.error('Trends section load failed:', err);
  }
}

// ---- GEO INTELLIGENCE (country-level hiring intake — darker & bigger
// circle means more postings from that country) ----
let geoMapFullInstance;

async function loadGeoFullSection() {

    if (sectionsLoaded.geo) {

        setTimeout(() => {
            if (geoMapFullInstance) {
                geoMapFullInstance.invalidateSize();
            }
        }, 200);

        return;
    }

    sectionsLoaded.geo = true;

    try {

        const res = await fetch(`${API}/geo-city-intake`);
        const data = await res.json();

        console.log("City Intake:", data);

        requestAnimationFrame(() => {

            geoMapFullInstance = L.map("geoMapContainer", {
                worldCopyJump: true,
                zoomControl: true
            });

            L.tileLayer(
                "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
                {
                    attribution: "&copy; OpenStreetMap contributors &copy; CARTO",
                    maxZoom: 18
                }
            ).addTo(geoMapFullInstance);

            if (data.length) {

                const counts = data.map(d => d.count);
                const min = Math.min(...counts);
                const max = Math.max(...counts);
                const scaleT = (count) => (max === min ? 1 : (count - min) / (max - min));

                // Light -> dark shade of the same hue as intake increases.
                const colorFor = (count) => {
                    const t = scaleT(count);
                    const light = [255, 179, 179];
                    const dark  = [139, 0, 0];
                    const rgb = light.map((c, i) => Math.round(c + (dark[i] - c) * t));
                    return `rgb(${rgb.join(",")})`;
                };

                const radiusFor = (count) => 8 + scaleT(count) * 26; // 8px..34px

                data.forEach(d => {
                    const marker = L.circleMarker([d.lat, d.lon], {
                        radius: radiusFor(d.count),
                        color: "rgba(255,255,255,0.4)",
                        weight: 1,
                        fillColor: colorFor(d.count),
                        fillOpacity: 0.8
                    }).addTo(geoMapFullInstance);

                    marker.bindTooltip(
                        `<strong>${d.city}</strong><br/>${d.count.toLocaleString()} postings`,
                        { direction: "top", sticky: true }
                    );
                });

                const bounds = L.latLngBounds(data.map(d => [d.lat, d.lon]));
                geoMapFullInstance.fitBounds(bounds, { padding: [60, 60] });

            } else {

                geoMapFullInstance.setView([20, 0], 2);

            }

            setTimeout(() => {

                geoMapFullInstance.invalidateSize();

            }, 300);

        });

    } catch (err) {

        console.error("Geo section load failed:", err);

    }

}
async function loadForecastSection() {
  if (sectionsLoaded.forecast) return;
  sectionsLoaded.forecast = true;

  const gridColor = 'rgba(255,255,255,0.05)';
  const fontColor = '#8b8ba7';

  try {
    const res = await fetch(`${API}/forecast`);
    const data = await res.json();

    const historicalMonths = data.historical.map(x => x.month);
    const historicalCounts = data.historical.map(x => x.count);

    // Build forecast month labels continuing on from the last historical month
    const lastDate = new Date(historicalMonths[historicalMonths.length - 1] + '-01');
    const forecastMonths = data.forecast_values.map((_, i) => {
      const d = new Date(lastDate);
      d.setMonth(d.getMonth() + i + 1);
      return d.toISOString().slice(0, 7);
    });

    const labels = [...historicalMonths, ...forecastMonths];

    // Historical series (nulls after the historical range)
    const historicalSeries = [...historicalCounts, ...forecastMonths.map(() => null)];

    // Forecast series (nulls before it starts, bridged from the last historical point)
    const forecastSeries = [
      ...historicalMonths.map(() => null),
      historicalCounts[historicalCounts.length - 1],
      ...data.forecast_values.slice(1)
    ];

    charts.forecast = new Chart(document.getElementById('forecastCanvas'), {
      type: 'line',
      data: {
        labels,
        datasets: [
          {
            label: 'Historical Postings',
            data: historicalSeries,
            borderColor: 'rgba(108,99,255,1)',
            backgroundColor: 'rgba(108,99,255,0.12)',
            tension: 0.4, fill: true, pointRadius: 4,
            pointBackgroundColor: 'rgba(108,99,255,1)',
          },
          {
            label: 'Forecast (3mo)',
            data: forecastSeries,
            borderColor: 'rgba(255,179,71,1)',
            backgroundColor: 'transparent',
            borderDash: [6, 4],
            tension: 0.4, pointRadius: 4,
            pointBackgroundColor: 'rgba(255,179,71,1)',
          }
        ]
      },
      options: { ...lineOptions(gridColor, fontColor), plugins: { legend: { display: true, labels: { color: fontColor } } } }
    });

    // Top hiring companies
    const compRes = await fetch(`${API}/top-companies`);
    const companies = await compRes.json();

    charts.topCompanies = new Chart(document.getElementById('topCompaniesCanvas'), {
      type: 'bar',
      data: {
        labels: companies.map(c => c.company),
        datasets: [{
          label: 'Postings',
          data: companies.map(c => c.count),
          backgroundColor: 'rgba(0,200,150,0.7)',
          borderRadius: 6
        }]
      },
      options: { indexAxis: 'y', ...barOptions(gridColor, fontColor, false) }
    });
  } catch (err) {
    console.error('Forecast section load failed:', err);
  }
}

// ---- EXPLORE JOBS ----
let exploreSearchDebounce;

async function loadExploreJobs(){

    const category     = document.getElementById("exploreCatFilter")?.value || "";
    const contractTime = document.getElementById("exploreCtFilter")?.value  || "";
    const keyword      = document.getElementById("exploreSearch")?.value    || "";

    try{

        const params = new URLSearchParams();
        if (category)     params.set("category", category);
        if (contractTime) params.set("contract_time", contractTime);
        if (keyword)       params.set("role", keyword);

        const response =
            await fetch(`${API}/search?${params.toString()}`);

        if (!response.ok) {
            throw new Error(`Search request failed (${response.status})`);
        }

        const data =
            await response.json();

        const grid =
            document.getElementById("exploreGrid");

        document.getElementById("exploreCount").innerHTML =
            `${data.count} Jobs`;

        if (!data.jobs.length) {
            grid.innerHTML = "<p>No jobs match those filters.</p>";
            return;
        }

        grid.innerHTML =
            data.jobs.map(job=>{

                const minS = job.salary_min != null ? `$${Math.round(job.salary_min).toLocaleString()}` : "N/A";
                const maxS = job.salary_max != null ? `$${Math.round(job.salary_max).toLocaleString()}` : "N/A";

                return `
            <div class="job-card">

                <h3>${job.title}</h3>

                <p>${job.company}</p>

                <p>${job.location_display}</p>

                <p>${minS} - ${maxS}</p>

                <a href="${job.redirect_url}" target="_blank">

                Apply

                </a>

            </div>

            `;
            }).join("");

    }

    catch(err){

        console.error(err);
        const grid = document.getElementById("exploreGrid");
        if (grid) grid.innerHTML = "<p>Couldn't load jobs — is the backend running?</p>";

    }

}

function debouncedExploreSearch() {
  clearTimeout(exploreSearchDebounce);
  exploreSearchDebounce = setTimeout(loadExploreJobs, 350);
}

function initExploreFilters() {
  const catFilter = document.getElementById("exploreCatFilter");
  const ctFilter  = document.getElementById("exploreCtFilter");
  const searchBox = document.getElementById("exploreSearch");

  if (catFilter) catFilter.addEventListener("change", loadExploreJobs);
  if (ctFilter)  ctFilter.addEventListener("change", loadExploreJobs);
  if (searchBox) searchBox.addEventListener("input", debouncedExploreSearch);
}

// ---- SPINNER ----
function showSpinner(text) {
  document.getElementById('spinnerOverlay').classList.add('show');
  document.getElementById('spinnerText').textContent = text || 'Processing...';
}
function hideSpinner() {
  document.getElementById('spinnerOverlay').classList.remove('show');
}

// ---- TOPBAR ICONS (notifications / settings) ----
// Purely functional wiring — the icons themselves are untouched visually.
function initTopbarIcons() {
  const bellBtn = document.getElementById('notifBtn');
  const settingsBtn = document.getElementById('settingsBtn');

  if (bellBtn) {
    bellBtn.addEventListener('click', () => {
      const dot = document.getElementById('notifDot');
      if (dot) dot.style.display = 'none';
      showTopbarToast("You're all caught up — no new notifications.");
    });
  }

  if (settingsBtn) {
    settingsBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      toggleSettingsMenu();
    });
  }
}

function showTopbarToast(msg) {
  let toast = document.getElementById('topbarToast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'topbarToast';
    toast.style.cssText = `
      position: fixed; top: 70px; right: 24px; z-index: 9999;
      background: #1a1a2e; color: #e0e0ff; border: 1px solid rgba(108,99,255,0.4);
      border-radius: 10px; padding: 12px 18px; font-family: 'Space Grotesk', sans-serif;
      font-size: 13px; box-shadow: 0 8px 24px rgba(0,0,0,0.4); opacity: 0;
      transition: opacity 0.25s; pointer-events: none;
    `;
    document.body.appendChild(toast);
  }
  toast.textContent = msg;
  requestAnimationFrame(() => { toast.style.opacity = '1'; });
  clearTimeout(toast._hideTimer);
  toast._hideTimer = setTimeout(() => { toast.style.opacity = '0'; }, 2600);
}

function toggleSettingsMenu() {
  const existing = document.getElementById('settingsMenu');
  if (existing) { existing.remove(); return; }

  const menu = document.createElement('div');
  menu.id = 'settingsMenu';
  menu.style.cssText = `
    position: fixed; top: 60px; right: 24px; z-index: 9999;
    background: #1a1a2e; border: 1px solid rgba(255,255,255,0.1); border-radius: 12px;
    padding: 8px; min-width: 190px; box-shadow: 0 8px 24px rgba(0,0,0,0.4);
    font-family: 'Space Grotesk', sans-serif;
  `;

  const items = [
    { icon: 'fa-user', label: 'Profile', action: openProfileModal },
    { icon: 'fa-sliders-h', label: 'Preferences', action: openPreferencesModal },
    { icon: 'fa-sign-out-alt', label: 'Sign Out', action: logout, danger: true }
  ];

  items.forEach(item => {
    const row = document.createElement('div');
    row.style.cssText = `
      padding: 10px 14px; font-size: 13px; cursor: pointer; border-radius: 8px;
      color: ${item.danger ? '#ff6b6b' : '#e0e0ff'};
    `;
    row.innerHTML = `<i class="fas ${item.icon}" style="width:18px;"></i> ${item.label}`;
    row.addEventListener('mouseover', () => { row.style.background = item.danger ? 'rgba(255,107,107,0.12)' : 'rgba(108,99,255,0.15)'; });
    row.addEventListener('mouseout',  () => { row.style.background = 'transparent'; });
    row.addEventListener('click', () => { item.action(); menu.remove(); });
    menu.appendChild(row);
  });

  document.body.appendChild(menu);

  setTimeout(() => {
    document.addEventListener('click', function closeMenu(e) {
      if (!menu.contains(e.target)) {
        menu.remove();
        document.removeEventListener('click', closeMenu);
      }
    });
  }, 0);
}

function closeAnySettingsModal() {
  const existing = document.getElementById('settingsModalOverlay');
  if (existing) existing.remove();
}

function getPreferences() {
  return JSON.parse(localStorage.getItem('joblens_preferences') || '{}');
}

function openProfileModal() {
  closeAnySettingsModal();
  const sess = JSON.parse(localStorage.getItem('joblens_session') || 'null') || {};

  const esc = v => (v || '').replace(/"/g, '&quot;');

  const overlay = document.createElement('div');
  overlay.id = 'settingsModalOverlay';
  overlay.className = 'settings-modal-overlay';
  overlay.innerHTML = `
    <div class="settings-modal">
      <h3><i class="fas fa-user" style="color:#6c63ff;margin-right:8px;"></i>Profile Details</h3>
      <p class="settings-sub">Update how your name and role appear across JobLens.</p>

      <div class="settings-field">
        <label>Full Name</label>
        <input type="text" id="profileNameInput" value="${esc(sess.name)}" placeholder="Your name"/>
      </div>
      <div class="settings-field">
        <label>Role / Title</label>
        <input type="text" id="profileRoleInput" value="${esc(sess.role)}" placeholder="e.g. Data Scientist"/>
      </div>
      <div class="settings-field">
        <label>Email (optional)</label>
        <input type="email" id="profileEmailInput" value="${esc(sess.email)}" placeholder="you@example.com"/>
      </div>

      <div class="settings-actions">
        <button class="settings-btn-cancel" id="profileCancelBtn">Cancel</button>
        <button class="settings-btn-save" id="profileSaveBtn">Save Changes</button>
      </div>
    </div>
  `;
  document.body.appendChild(overlay);

  overlay.addEventListener('click', (e) => { if (e.target === overlay) closeAnySettingsModal(); });
  document.getElementById('profileCancelBtn').addEventListener('click', closeAnySettingsModal);

  document.getElementById('profileSaveBtn').addEventListener('click', () => {
    const name  = document.getElementById('profileNameInput').value.trim()  || 'User';
    const role  = document.getElementById('profileRoleInput').value.trim() || 'Analyst';
    const email = document.getElementById('profileEmailInput').value.trim();

    const updated = { ...sess, name, role, email };
    localStorage.setItem('joblens_session', JSON.stringify(updated));

    document.getElementById('sidebarName').textContent   = name;
    document.getElementById('sidebarRole').textContent   = role;
    document.getElementById('sidebarAvatar').textContent = name[0].toUpperCase();

    closeAnySettingsModal();
    showTopbarToast('Profile updated.');
  });
}

function openPreferencesModal() {
  closeAnySettingsModal();
  const prefs = getPreferences();
  const esc = v => (v || '').replace(/"/g, '&quot;');

  const overlay = document.createElement('div');
  overlay.id = 'settingsModalOverlay';
  overlay.className = 'settings-modal-overlay';
  overlay.innerHTML = `
    <div class="settings-modal">
      <h3><i class="fas fa-sliders-h" style="color:#00e5ff;margin-right:8px;"></i>Preferences</h3>
      <p class="settings-sub">Personalise your default search and notification behaviour.</p>

      <div class="settings-field">
        <label>Default Search Location</label>
        <input type="text" id="prefDefaultLocation" value="${esc(prefs.defaultLocation)}" placeholder="e.g. London"/>
      </div>

      <div class="settings-field">
        <label>Salary Display Currency</label>
        <select id="prefCurrency">
          <option value="USD" ${prefs.currency === 'USD' ? 'selected' : ''}>USD ($)</option>
          <option value="GBP" ${prefs.currency !== 'USD' ? 'selected' : ''}>GBP (£)</option>
        </select>
      </div>

      <div class="settings-toggle-row">
        <div>
          <div class="settings-toggle-label">Email Notifications</div>
          <div class="settings-toggle-sub">Get notified about new matching postings</div>
        </div>
        <label class="settings-switch">
          <input type="checkbox" id="prefNotifications" ${prefs.notifications ? 'checked' : ''}/>
          <span class="slider"></span>
        </label>
      </div>

      <div class="settings-toggle-row">
        <div>
          <div class="settings-toggle-label">Compact Job Cards</div>
          <div class="settings-toggle-sub">Show more results per row</div>
        </div>
        <label class="settings-switch">
          <input type="checkbox" id="prefCompact" ${prefs.compact ? 'checked' : ''}/>
          <span class="slider"></span>
        </label>
      </div>

      <div class="settings-actions">
        <button class="settings-btn-cancel" id="prefsCancelBtn">Cancel</button>
        <button class="settings-btn-save" id="prefsSaveBtn">Save Preferences</button>
      </div>
    </div>
  `;
  document.body.appendChild(overlay);

  overlay.addEventListener('click', (e) => { if (e.target === overlay) closeAnySettingsModal(); });
  document.getElementById('prefsCancelBtn').addEventListener('click', closeAnySettingsModal);

  document.getElementById('prefsSaveBtn').addEventListener('click', () => {
    const updated = {
      defaultLocation: document.getElementById('prefDefaultLocation').value.trim(),
      currency: document.getElementById('prefCurrency').value,
      notifications: document.getElementById('prefNotifications').checked,
      compact: document.getElementById('prefCompact').checked,
    };
    localStorage.setItem('joblens_preferences', JSON.stringify(updated));

    if (updated.defaultLocation && !document.getElementById('searchLocation').value) {
      document.getElementById('searchLocation').value = updated.defaultLocation;
    }

    closeAnySettingsModal();
    showTopbarToast('Preferences saved.');
  });
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


if (name === "explore") {

    loadExploreJobs();

} else if (name === "trends") {

    loadTrendsSection();

} else if (name === "geo") {

    loadGeoFullSection();

} else if (name === "forecast") {

    loadForecastSection();

}
}
async function predictSalary() {

    const title = document.getElementById("salaryTitle").value;
    const location = document.getElementById("salaryLocation").value;
    const category = document.getElementById("salaryCat").value;
    const contract = document.getElementById("salaryCt").value;

    if (!title.trim()) {
        alert("Enter a job title.");
        return;
    }

    try {

        const response = await fetch(`${API}/predict-salary`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                title,
                location,
                category,
                contract_time: contract
            })
        });

        const data = await response.json();

        if (data.error) {
            alert("Salary prediction failed: " + data.error);
            return;
        }

        // Guard against null/NaN salary values (e.g. no close matches found
        // for this title/location/category combo) so we show "N/A" instead
        // of a broken "$NaN" string.
        const fmt = v => (v === null || v === undefined || isNaN(v))
            ? "N/A"
            : `$${Math.round(v).toLocaleString()}`;

        const result = document.getElementById("salaryResult");

        result.style.display = "block";

        result.innerHTML = `
        <div class="salary-result-card">

            <div class="salary-result-title">
                Estimated salary for <em>${title}</em>
            </div>

            <div class="salary-bands">

                <div class="salary-band">
                    <div class="band-label">Minimum</div>
                    <div class="band-value green">${fmt(data.salary_min)}</div>
                </div>

                <div class="salary-band highlight">
                    <div class="band-label">Average</div>
                    <div class="band-value large">${fmt(data.salary_mid)}</div>
                </div>

                <div class="salary-band">
                    <div class="band-label">Maximum</div>
                    <div class="band-value cyan">${fmt(data.salary_max)}</div>
                </div>

            </div>

        </div>
        `;

    }
    catch (err) {

        console.error(err);

        alert("Salary prediction failed.");

    }

}

async function classifyJob() {

    const title =
        document.getElementById("classifyTitle").value;

    const description =
        document.getElementById("classifyDesc").value;

    if (!title.trim()) {

        alert("Enter a job title.");

        return;

    }

    try {

        const response = await fetch(`${API}/classify`, {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({

                title,

                description

            })

        });

        const data = await response.json();

        if (data.error) {
            alert("Classification failed: " + data.error);
            return;
        }

        const result =
            document.getElementById("classifyResult");

        result.style.display = "block";

        const barColors = ["#00e5ff", "#6c63ff", "#ff6b6b"];

        const top3Html = (data.top3 || []).map((row, i) => `
            <div class="classify-row">
                <div class="classify-label">${row.category}</div>
                <div class="classify-bar-wrap">
                    <div class="classify-bar" style="width:${Math.round(row.probability * 100)}%; background:${barColors[i] || '#8b8ba7'};"></div>
                </div>
                <div class="classify-prob">${Math.round(row.probability * 100)}%</div>
            </div>
        `).join("");

        result.innerHTML = `

        <div class="classify-result-card">

            <div class="classify-predicted">

                Predicted Category:

                <strong>${data.category}</strong>

            </div>

            <div class="classify-top3">
                ${top3Html}
            </div>

        </div>

        `;

    }

    catch(err){

        console.error(err);

        alert("Classification failed.");

    }

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
    initTopbarIcons();
    initExploreFilters();

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

});
