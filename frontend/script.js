const API_URL = 'http://localhost:8000';

function getToken() { return localStorage.getItem('token'); }
function setToken(token) { localStorage.setItem('token', token); }
function clearToken() { localStorage.removeItem('token'); }

async function apiRequest(endpoint, method = 'GET', body = null) {
    const headers = { 'Content-Type': 'application/json' };
    const token = getToken();
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const config = { method, headers };
    if (body) config.body = JSON.stringify(body);

    try {
        const response = await fetch(`${API_URL}${endpoint}`, config);
        
        if (response.status === 401) {
            logout();
            throw new Error('Сессия истекла. Войдите снова.');
        }
        
        if (response.status === 204) {
            return null;
        }
        
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || 'Произошла ошибка');
        }
        return data;
    } catch (error) {
        throw error;
    }
}

function switchTab(tab) {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.form-section').forEach(f => f.classList.add('hidden'));
    
    if (tab === 'login') {
        document.querySelector('.tab-btn:nth-child(1)').classList.add('active');
        document.getElementById('login-form').classList.remove('hidden');
    } else {
        document.querySelector('.tab-btn:nth-child(2)').classList.add('active');
        document.getElementById('register-form').classList.remove('hidden');
    }
    document.getElementById('auth-error').innerText = '';
}

async function handleLogin(e) {
    e.preventDefault();
    const username = document.getElementById('login-username').value;
    const password = document.getElementById('login-password').value;
    try {
        const data = await apiRequest('/auth/login', 'POST', { username, password });
        setToken(data.access_token);
        showApp();
    } catch (err) {
        document.getElementById('auth-error').innerText = err.message;
    }
}

async function handleRegister(e) {
    e.preventDefault();
    const username = document.getElementById('reg-username').value;
    const password = document.getElementById('reg-password').value;
    const role = document.getElementById('reg-role').value;
    try {
        await apiRequest('/auth/register', 'POST', { username, password, role });
        alert('Регистрация успешна! Теперь войдите.');
        switchTab('login');
    } catch (err) {
        document.getElementById('auth-error').innerText = err.message;
    }
}

function logout() {
    clearToken();
    document.getElementById('auth-screen').classList.remove('hidden');
    document.getElementById('app-screen').classList.add('hidden');
}

let currentUserRole = 'seller';

async function showApp() {
    try {
        const user = await apiRequest('/auth/me');
        currentUserRole = user.role;
        
        document.getElementById('auth-screen').classList.add('hidden');
        document.getElementById('app-screen').classList.remove('hidden');
        
        document.getElementById('user-info').innerText = 
            `${user.username} (${user.role === 'admin' ? 'Администратор' : 'Продавец'})`;
        
        if (user.role !== 'admin') {
            document.getElementById('musicians-section').classList.add('hidden');
            document.getElementById('add-disc-form').classList.add('hidden');
        } else {
            document.getElementById('musicians-section').classList.remove('hidden');
            document.getElementById('add-disc-form').classList.remove('hidden');
        }
        
        loadAllData();
    } catch (err) {
        logout();
    }
}

async function loadMusicians() {
    try {
        const musicians = await apiRequest('/musicians');
        const tbody = document.querySelector('#musicians-table tbody');
        tbody.innerHTML = '';
        
        musicians.forEach(m => {
            tbody.innerHTML += `
                <tr>
                    <td>${m.id}</td>
                    <td>${m.name}</td>
                    <td>${m.genre}</td>
                    <td><button class="btn-danger" onclick="deleteMusician(${m.id})">Удалить</button></td>
                </tr>
            `;
        });
        
        const select = document.getElementById('disc-musician');
        select.innerHTML = '<option value="">Выберите музыканта</option>';
        musicians.forEach(m => {
            select.innerHTML += `<option value="${m.id}">${m.name}</option>`;
        });
    } catch (err) { console.error(err); }
}

async function addMusician(e) {
    e.preventDefault();
    const name = document.getElementById('musician-name').value;
    const genre = document.getElementById('musician-genre').value;
    
    try {
        await apiRequest('/musicians', 'POST', { name, genre });
        e.target.reset();
        loadMusicians();
    } catch (err) { alert('Ошибка: ' + err.message); }
}

async function deleteMusician(id) {
    if(!confirm('Удалить музыканта?')) return;
    try {
        await apiRequest(`/musicians/${id}`, 'DELETE');
        loadMusicians();
    } catch (err) { alert('Ошибка: ' + err.message); }
}

async function loadDiscs() {
     try {
        const discs = await apiRequest('/discs');
        const musicians = await apiRequest('/musicians');
        const tbody = document.querySelector('#discs-table tbody');
        tbody.innerHTML = '';
        
        discs.forEach(d => {
            const musician = musicians.find(m => m.id === d.musician_id);
            const musicianName = musician ? musician.name : 'Неизвестный';
            
            let actionButtons = '';
            if (currentUserRole === 'admin') {
                actionButtons = `
                    <button class="btn-warning" onclick="restockDisc(${d.id})" style="margin-right:5px; background:#f59e0b; color:white; padding: 4px 8px; font-size: 12px;">Пополнить</button>
                    <button class="btn-danger" onclick="deleteDisc(${d.id})" style="padding: 4px 8px; font-size: 12px;">Удалить</button>
                `;
            }
            
            tbody.innerHTML += `
                <tr>
                    <td>${d.id}</td>
                    <td>${d.title}</td>
                    <td>${musicianName}</td>
                    <td>${d.price.toFixed(2)} руб.</td>
                    <td style="font-weight: bold; color: ${d.stock === 0 ? 'red' : 'green'}">${d.stock} шт.</td>
                    <td>${actionButtons}</td>
                </tr>
            `;
        });
        
        const select = document.getElementById('sale-disc');
        select.innerHTML = '<option value="">Выберите диск</option>';
        discs.forEach(d => {
            if (d.stock > 0) {
                const musician = musicians.find(m => m.id === d.musician_id);
                const musicianName = musician ? musician.name : 'Неизвестный';
                select.innerHTML += `<option value="${d.id}">${d.title} (${musicianName}) - ${d.stock} шт.</option>`;
            }
        });
    } catch (err) { console.error(err); }
}

async function addDisc(e) {
    e.preventDefault();
    const title = document.getElementById('disc-title').value;
    const musician_id = parseInt(document.getElementById('disc-musician').value);
    const price = parseFloat(document.getElementById('disc-price').value);
    const stock = parseInt(document.getElementById('disc-stock').value);

    try {
        await apiRequest('/discs', 'POST', { title, musician_id, price, stock });
        e.target.reset();
        loadDiscs();
    } catch (err) { alert('Ошибка: ' + err.message); }
}

async function deleteDisc(id) {
    if(!confirm('Удалить диск?')) return;
    try {
        await apiRequest(`/discs/${id}`, 'DELETE');
        loadDiscs();
    } catch (err) { alert('Ошибка: ' + err.message); }
}

async function restockDisc(discId) {
    const qtyStr = prompt("Введите количество дисков для пополнения остатка:");
    if (!qtyStr) return;
    
    const quantity = parseInt(qtyStr);
    if (isNaN(quantity) || quantity <= 0) {
        alert("Ошибка: введите корректное положительное число");
        return;
    }

    try {
        await apiRequest(`/discs/${discId}/restock`, 'POST', { quantity });
        alert("✅ Остаток успешно пополнен!");
        loadDiscs();
    } catch (err) {
        alert("Ошибка: " + err.message);
    }
}

async function makeSale(e) {
    e.preventDefault();
    const disc_id = parseInt(document.getElementById('sale-disc').value);
    const quantity = parseInt(document.getElementById('sale-qty').value);
    const msgEl = document.getElementById('sale-msg');
    msgEl.className = 'info-msg';
    msgEl.innerText = '';

    try {
        await apiRequest('/sales', 'POST', { disc_id, quantity });
        msgEl.innerText = 'Продажа успешно оформлена!';
        e.target.reset();
        loadDiscs();
        loadSales();
    } catch (err) {
        msgEl.className = 'info-msg error';
        msgEl.innerText = 'Ошибка: ' + err.message;
    }
}

async function loadSales() {
    try {
        const sales = await apiRequest('/sales');
        const discs = await apiRequest('/discs');
        const tbody = document.querySelector('#sales-table tbody');
        tbody.innerHTML = '';
        
        sales.forEach(s => {
            const disc = discs.find(d => d.id === s.disc_id);
            const discTitle = disc ? disc.title : 'Удаленный диск';
            const date = new Date(s.sold_at).toLocaleString('ru-RU');
            
            tbody.innerHTML += `
                <tr>
                    <td>${s.id}</td>
                    <td>${discTitle}</td>
                    <td>${s.quantity}</td>
                    <td>${s.total_price.toFixed(2)} руб.</td>
                    <td>${date}</td>
                </tr>
            `;
        });
    } catch (err) { console.error(err); }
}

function loadAllData() {
    loadMusicians();
    loadDiscs();
    loadSales();
}

window.onload = () => {
    if (getToken()) {
        showApp();
    }
};