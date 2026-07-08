// =============================
//  JobLens — Auth Logic
// =============================

// --- Tab Switching ---
function switchTab(tab) {
  const loginForm   = document.getElementById('loginForm');
  const registerForm = document.getElementById('registerForm');
  const loginTab    = document.getElementById('loginTab');
  const registerTab = document.getElementById('registerTab');
  const indicator   = document.getElementById('tabIndicator');

  if (tab === 'login') {
    loginForm.classList.add('active');
    registerForm.classList.remove('active');
    loginTab.classList.add('active');
    registerTab.classList.remove('active');
    indicator.classList.remove('right');
  } else {
    registerForm.classList.add('active');
    loginForm.classList.remove('active');
    registerTab.classList.add('active');
    loginTab.classList.remove('active');
    indicator.classList.add('right');
  }
}

// --- Toggle Password Visibility ---
function togglePwd(inputId, icon) {
  const input = document.getElementById(inputId);
  if (input.type === 'password') {
    input.type = 'text';
    icon.classList.replace('fa-eye', 'fa-eye-slash');
  } else {
    input.type = 'password';
    icon.classList.replace('fa-eye-slash', 'fa-eye');
  }
}

// --- Password Strength ---
document.addEventListener('DOMContentLoaded', () => {
  const pwdInput = document.getElementById('regPassword');
  if (pwdInput) {
    pwdInput.addEventListener('input', () => {
      const val = pwdInput.value;
      const fill = document.getElementById('strengthFill');
      const label = document.getElementById('strengthLabel');
      let score = 0;
      if (val.length >= 8) score++;
      if (/[A-Z]/.test(val)) score++;
      if (/[0-9]/.test(val)) score++;
      if (/[^A-Za-z0-9]/.test(val)) score++;

      const configs = [
        { width: '0%',   bg: 'transparent', text: '' },
        { width: '25%',  bg: '#ff6b6b',      text: 'Weak' },
        { width: '50%',  bg: '#ffb347',      text: 'Fair' },
        { width: '75%',  bg: '#6c63ff',      text: 'Good' },
        { width: '100%', bg: '#00c896',      text: 'Strong 🔒' },
      ];
      fill.style.width = configs[score].width;
      fill.style.background = configs[score].bg;
      label.textContent = configs[score].text;
    });
  }
});

// --- Show Toast ---
function showToast(msg, type = 'success') {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = `toast ${type} show`;
  setTimeout(() => t.classList.remove('show'), 3000);
}

// --- Handle Login ---
function handleLogin() {
  const email = document.getElementById('loginEmail').value.trim();
  const password = document.getElementById('loginPassword').value;

  if (!email || !password) {
    return showToast('Please fill in all fields.', 'error');
  }
  if (!isValidEmail(email)) {
    return showToast('Enter a valid email address.', 'error');
  }

  // Check stored users
  const users = JSON.parse(localStorage.getItem('joblens_users') || '[]');
  const found = users.find(u => u.email === email && u.password === btoa(password));

  if (!found) {
    return showToast('Invalid credentials. Try Demo Access.', 'error');
  }

  // Store session
  localStorage.setItem('joblens_session', JSON.stringify({ name: found.name, email: found.email, role: found.role }));
  showToast('Welcome back, ' + found.name + '!', 'success');
  setTimeout(() => { window.location.href = 'dashboard.html'; }, 1000);
}

// --- Demo Login ---
function demoLogin() {
  localStorage.setItem('joblens_session', JSON.stringify({
    name: 'Demo User', email: 'demo@joblens.ai', role: 'Data Scientist'
  }));
  showToast('Launching Demo...', 'success');
  setTimeout(() => { window.location.href = 'dashboard.html'; }, 800);
}

// --- Handle Register ---
function handleRegister() {
  const firstName = document.getElementById('regFirstName').value.trim();
  const lastName  = document.getElementById('regLastName').value.trim();
  const email     = document.getElementById('regEmail').value.trim();
  const role      = document.getElementById('regRole').value.trim();
  const password  = document.getElementById('regPassword').value;
  const confirm   = document.getElementById('regConfirm').value;
  const agreed    = document.getElementById('agreeTerms').checked;

  if (!firstName || !lastName || !email || !password || !confirm) {
    return showToast('Please fill in all fields.', 'error');
  }
  if (!isValidEmail(email)) {
    return showToast('Enter a valid email address.', 'error');
  }
  if (password.length < 8) {
    return showToast('Password must be at least 8 characters.', 'error');
  }
  if (password !== confirm) {
    return showToast('Passwords do not match.', 'error');
  }
  if (!agreed) {
    return showToast('Please accept the Terms & Privacy Policy.', 'error');
  }

  const users = JSON.parse(localStorage.getItem('joblens_users') || '[]');
  if (users.find(u => u.email === email)) {
    return showToast('Account already exists. Sign in instead.', 'error');
  }

  users.push({ name: `${firstName} ${lastName}`, email, role, password: btoa(password) });
  localStorage.setItem('joblens_users', JSON.stringify(users));
  localStorage.setItem('joblens_session', JSON.stringify({ name: `${firstName} ${lastName}`, email, role }));

  showToast('Account created! Launching...', 'success');
  setTimeout(() => { window.location.href = 'dashboard.html'; }, 1000);
}

function isValidEmail(e) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e);
}
