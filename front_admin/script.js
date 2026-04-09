// GLOBAL VARIABLES
let employees = [];
let accessToken = null; // access token in memory only
let currentUser = null;
const tbody = document.getElementById("employeeTableBody");
let deleteHandler;

// ================================
// UTILITY FUNCTIONS
// ================================
function showLoading(btn, spinner) {
    if (btn) btn.disabled = true;
    if (spinner) spinner.classList.remove("hidden");
}

function hideLoading(btn, spinner) {
    if (btn) btn.disabled = false;
    if (spinner) spinner.classList.add("hidden");
}

function toggleSidebar() {
    document.getElementById("sidebar").classList.toggle("collapsed");
}

function showSection(id) {

    document.querySelectorAll(".content-section").forEach(sec => {
        sec.classList.remove("active");
    });

    const section = document.getElementById(id);

    if(section){
        section.classList.add("active");
    }

}

// ================================
// TOAST NOTIFICATIONS
// ================================
function showToast(message, type = 'info', duration = 5000) {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <div class="toast-content">
            <div class="toast-message">${message}</div>
        </div>
        <button class="toast-close" onclick="closeToast(this)">×</button>
    `;

    container.appendChild(toast);

    // Trigger animation
    setTimeout(() => toast.classList.add('show'), 10);

    // Auto remove
    if (duration > 0) {
        setTimeout(() => closeToast(toast.querySelector('.toast-close')), duration);
    }
}

function closeToast(closeBtn) {
    const toast = closeBtn.closest('.toast');
    if (!toast) return;

    toast.classList.add('fade-out');
    setTimeout(() => {
        if (toast.parentNode) {
            toast.parentNode.removeChild(toast);
        }
    }, 300);
}

async function resendOTP() {
    if (!currentPaymentReference) {
        showToast('No active payment reference', 'error');
        return;
    }
    
    try {
        showLoading(document.getElementById('resendOtpBtn'));
        const res = await apiRequest('/api/payments/resend_otp/', {
            method: 'POST',
            body: JSON.stringify({ reference: currentPaymentReference })
        });
        showToast('OTP sent successfully', 'success');
        startOtpCountdown(); // Restart the timer
    } catch (err) {
        showToast('Failed to resend OTP', 'error');
    } finally {
        hideLoading(document.getElementById('resendOtpBtn'));
    }
}

// ================================
// API WRAPPER
// ================================
async function apiRequest(url, options = {}) {
    try {
        // Include access token in memory
        const headers = {
            "Content-Type": "application/json",
            ...(accessToken ? { "Authorization": "Bearer " + accessToken } : {}),
            ...options.headers
        };

        const res = await fetch(url, {
            credentials: "include", // send refresh token cookie automatically
            headers,
            ...options
        });

        // If access token expired, try refresh
        if (res.status === 401) {
            const refreshed = await refreshAccessToken();
            if (refreshed) return apiRequest(url, options);
            logout();
            throw new Error("Session expired. Please login again.");
        }

        if (!res.ok) throw new Error(`API error: ${res.statusText}`);
        return await res.json();
    } catch (err) {
        console.error(err);
        throw err;
    }
}

async function apiFetch(url, options = {}) {

    let accessToken = localStorage.getItem("access_token");

    let response = await fetch(url, {
        ...options,
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${accessToken}`
        }
    });

    if (response.status === 401) {

        // refresh token
        const refresh = await fetch("/api/token/refresh/", {
            method: "POST",
            credentials: "include"
        });

        const data = await refresh.json();

        localStorage.setItem("access_token", data.access);

        return fetch(url, {
            ...options,
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${data.access}`
            }
        });

    }

    return response;
}

async function refreshAccessToken() {
    try {
        const res = await fetch("/api/token/refresh/", {
            method: "POST",
            credentials: "include" // httpOnly refresh cookie
        });
        if (!res.ok) return false;
        const data = await res.json();
        accessToken = data.access;
        return true;
    } catch (err) {
        return false;
    }
}

function logout() {
    fetch("/api/logout/", { method: "POST", credentials: "include" });
    accessToken = null;
    sessionStorage.removeItem("isLoggedIn"); // Clear session storage
    window.location.href = "/login/";
}

// ================================
// FORM VALIDATION
// ================================
function validateEmployeeForm(data) {
    if (!data.name) throw new Error("Name required");
    if (!data.email || !data.email.includes("@")) throw new Error("Valid email required");
    if (!data.salary || isNaN(data.salary)) throw new Error("Salary must be numeric");
    if (!data.account_number || data.account_number.length < 10) throw new Error("Valid account number required");
}

// ================================
// EMPLOYEE TABLE RENDERING
// ================================
function renderEmployees(employees) {
    tbody.innerHTML = "";
    const fragment = document.createDocumentFragment();
    
    employees.forEach(emp => {
        const row = document.createElement("tr");

        ["id","name","employee_type","location","bank_name","salary"].forEach(key => {
            const td = document.createElement("td");
            td.textContent = key === "salary"
                ? `₦${emp[key]}`
                : emp[key];

            row.appendChild(td);
        });

        const tdActions = document.createElement("td");
        const deleteBtn = document.createElement("button");

        deleteBtn.className = "btn btn-sm btn-danger";
        deleteBtn.textContent = "Delete";

        deleteBtn.addEventListener("click", () => {
            if (deleteHandler) deleteHandler(emp.id);
        });
        tdActions.appendChild(deleteBtn);
        row.appendChild(tdActions);

        fragment.appendChild(row);
    });
    tbody.appendChild(fragment);
}

function setDeleteHandler(fn) { deleteHandler = fn; }

// ================================
// EMPLOYEE CRUD
// ================================
async function loadEmployees(page=1) {

    try {

        const response = await apiRequest(`/api/employees/?page=${page}`);
        // Handle paginated response from DRF
        employees = response.results || response;
        renderEmployees(employees);
        // populate dropdowns for other modals
        populateEmployeeSelect("clockEmployee");
        populateEmployeeSelect("deductionEmployee");
        populateEmployeeSelect("paymentEmployee");
    } catch (err) { 
        showToast(`Failed to load employees: ${err.message}`, 'error');
    }
}

async function handleDelete(id) {
    if (!confirm("Delete employee?")) return;
    try {
        await apiRequest(`/api/employees/${id}/`, { method: "DELETE" });
        loadEmployees();
        showToast('Employee deleted successfully', 'success');
    } catch (err) { 
        showToast('Failed to delete employee', 'error');
    }
}


        // ===== PRODUCTION VALIDATION =====
function validateEmployeePayload(payload) {

    // Trim string fields safely
    const name = payload.name?.trim();
    const email = payload.email?.trim();
    const location = payload.location?.trim();
    const phone = payload.phone?.trim();
    const bankName = payload.bank_name?.trim();
    const accountNumber = payload.account_number?.trim();
    const accountHolder = payload.account_holder?.trim();
    const employeeType = payload.employee_type?.trim();
    const salary = Number(payload.salary);

    // Required Fields Check
    if (
        !name || !email || !location || !phone ||
        !bankName || !accountNumber || !accountHolder ||
        !employeeType 
    ) {
        throw new Error("All fields are required.");
    }

    // Salary Validation
    if (isNaN(salary) || salary <= 0) {
        throw new Error("Salary must be a valid number greater than 0.");
    }

    // Email Format Validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
        throw new Error("Invalid email format.");
    }

    // Nigerian Phone Validation (basic)
    const phoneRegex = /^[0-9]{10,15}$/;
    if (!phoneRegex.test(phone)) {
        throw new Error("Phone number must be 10–15 digits.");
    }

    // bank Account Validation (Nigeria = 10 digits)
    if (!/^[0-9]{10}$/.test(accountNumber)) {
        throw new Error("Account number must be exactly 10 digits.");
    }

    // Prevent Very Short Names
    if (name.length < 3) {
        throw new Error("Employee name is too short.");
    }

    return true;
}

async function handleCreateEmployee(e) {
    e.preventDefault();

    const payload = {
        name: document.getElementById("newEmployeeName").value.trim(),
        employee_type: document.getElementById("newEmployeeType").value.trim(),
        location: document.getElementById("newEmployeeLocation").value.trim(),
        salary: document.getElementById("newEmployeeSalary").value.trim(),
        email: document.getElementById("newEmployeeEmail").value.trim(),
        phone: document.getElementById("newEmployeePhone").value.trim(),
        bank_name: document.getElementById("newEmployeeBankName").value.trim(),
        account_number: document.getElementById("newEmployeeAccountNumber").value.trim(),
        account_holder: document.getElementById("newEmployeeAccountHolder").value.trim()
    };

    try {
        // run prooduction vali
        validateEmployeePayload(payload);

        if (typeof showLoading === "function") {
            showLoading(document.getElementById("createEmployeeBtn"),
            document.getElementById("addEmployeeSpinner")
        );
        }

    await apiRequest("/api/employees/", {
            method: "POST",
            body: JSON.stringify(payload)
        });

        showToast("Employee created successfully!", 'success');
        loadEmployees();
        closeModal("addEmployeeModal");
    } catch (err) {
        showToast(`Error creating employee: ${err.message}`, 'error');
    } finally {
        if (typeof hideLoading === "function"){
            hideLoading(document.getElementById("createEmployeeBtn"),
            document.getElementById("addEmployeeSpinner"));
            } 
    }
}

// ==========
// fetch logged user
// ========
async function loadCurrentUser() {
    try {
        const user = await apiRequest("/api/users/");
        currentUser = user;
        applyRolePermissions(user);
    } catch (err) {
        console.error("Failed to load user:", err);
    }
}
function applyRolePermissions(user) {

    // Hide everything first (safe default)
    document.getElementById("admin-controls").style.display = "none";
    document.getElementById("payment-section").style.display = "none";
    document.getElementById("employee-section").style.display = "none";

    // Superuser → sees everything
    if (user.is_superuser) {
        document.getElementById("admin-controls").style.display = "block";
        document.getElementById("payment-section").style.display = "block";
        document.getElementById("employee-section").style.display = "block";
        return;
    }

    // Employee Admin
    if (user.is_employee_admin) {
        document.getElementById("employee-section").style.display = "block";
    }

    // Payroll Admin
    if (user.is_payment_admin) {
        document.getElementById("payment-section").style.display = "block";
    }

    // General Admin role
    // if (user.role === "admin") {
    //     document.getElementById("admin-controls").style.display = "block";
    // }
}

// ================================
// EXTRA UTILITIES & HANDLERS
// ================================

async function handleAddDeduction(e) {
    e.preventDefault();
    const empId = document.getElementById('deductionEmployee').value;
    const amount = document.getElementById('deductionAmount').value;
    const reason = document.getElementById('deductionReason').value.trim();
    if (!empId || !amount || !reason) {
        showToast('All fields required', 'warning');
        return;
    }
    try {
        showLoading(document.querySelector('#addDeductionModal .btn-primary'));
        await apiRequest('/api/deductions/', {
            method: 'POST',
            body: JSON.stringify({
                employee: empId,
                amount,
                reason
            })
        });
        showToast('Deduction added successfully', 'success');
        closeModal('addDeductionModal');
        // optionally reload relevant tables
    } catch (err) {
        showToast('Failed to add deduction', 'error');
    } finally {
        hideLoading(document.querySelector('#addDeductionModal .btn-primary'));
    }
}

async function handleAddCompany(e) {
    e.preventDefault();
    // implementation left minimal; production logic should validate fields and send POST
    const form = e.target;
    const payload = {};
    Array.from(form.elements).forEach(el => {
        if (el.name) payload[el.name] = el.value;
    });
    try {
        showLoading(form.querySelector('.btn-primary'));
        await apiRequest('/api/companies/', {
            method: 'POST',
            body: JSON.stringify(payload)
        });
        showToast('Company added successfully', 'success');
        closeModal('addCompanyModal');
    } catch (err) {
        showToast('Failed to add company', 'error');
    } finally {
        hideLoading(form.querySelector('.btn-primary'));
    }
}

function populateEmployeeSelect(selectId) {
    const select = document.getElementById(selectId);
    if (!select) return;
    select.innerHTML = "";
    employees.forEach(emp => {
        const opt = document.createElement("option");
        opt.value = emp.id;
        opt.textContent = `${emp.name} (${emp.employee_type})`;
        select.appendChild(opt);
    });
}

function showAddEmployeeModal() {
    document.getElementById('addEmployeeModal').classList.add('active');
}
function showClockInModal() {
    document.getElementById('clockInModal').classList.add('active');
}
function showAddDeductionModal() {
    document.getElementById('addDeductionModal').classList.add('active');
}
function showIndividualPaymentModal() {
    document.getElementById('individualPaymentModal').classList.add('active');
}
let currentPaymentReference = null;
let otpTimerInterval = null;

function showBulkPaymentModal() {
    document.getElementById('bulkPaymentModal').classList.add('active');
    populateBulkTable();
}

function populateBulkTable() {
    const tbody = document.getElementById('bulkPaymentTableBody');
    if (!tbody) return;
    tbody.innerHTML = '';
    employees.forEach(emp => {
        const tr = document.createElement('tr');
        const chk = document.createElement('input');
        chk.type = 'checkbox';
        chk.value = emp.id;
        chk.addEventListener('change', updateBulkSummary);
        const tdChk = document.createElement('td');
        tdChk.appendChild(chk);
        tr.appendChild(tdChk);

        ['employee_id','name','bank_name','salary'].forEach(key => {
            const td = document.createElement('td');
            td.textContent = key === 'salary' ? `₦${emp[key]}` : emp[key];
            tr.appendChild(td);
        });
        tbody.appendChild(tr);
    });
    updateBulkSummary();
}

function toggleAllBulkPayments() {
    const all = document.getElementById('selectAllBulk');
    const checkboxes = document.querySelectorAll('#bulkPaymentTableBody input[type=checkbox]');
    checkboxes.forEach(cb => cb.checked = all.checked);
    updateBulkSummary();
}

function updateBulkSummary() {
    const checked = Array.from(document.querySelectorAll('#bulkPaymentModal tbody input[type=checkbox]:checked'));
    const total = checked.reduce((sum, chk) => {
        const row = chk.closest('tr');
        const amt = parseFloat(row.cells[4].textContent.replace(/[^0-9\.]/g, '')) || 0;
        return sum + amt;
    }, 0);
    document.getElementById('bulkTotalEmployees').textContent = checked.length;
    document.getElementById('bulkTotalAmount').textContent = `₦${total}`;
}
function populateCompanyGuards() {
    const sel = document.getElementById('companyAssignedGuards');
    if (!sel) return;
    sel.innerHTML = '';
    employees.forEach(emp => {
        const opt = document.createElement('option');
        opt.value = emp.id;
        opt.textContent = emp.name;
        sel.appendChild(opt);
    });
}

function showAddCompanyModal() {
    populateCompanyGuards();
    document.getElementById('addCompanyModal').classList.add('active');
}

function closeModal(id) {
    const m = document.getElementById(id);
    if (m) m.classList.remove('active');
}

// camera helpers (basic)
let cameraStream;
async function startCamera() {
    try {
        cameraStream = await navigator.mediaDevices.getUserMedia({ video: true });
        const video = document.getElementById('cameraVideo');
        video.srcObject = cameraStream;
        document.getElementById('captureBtn').disabled = false;
    } catch (err) {
        showToast('Camera access denied. Please allow camera permissions.', 'error');
    }
}
function capturePhoto() {
    const video = document.getElementById('cameraVideo');
    const canvas = document.getElementById('cameraCanvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d').drawImage(video, 0, 0);
    const dataUrl = canvas.toDataURL('image/png');
    const img = document.createElement('img');
    img.src = dataUrl;
    const container = document.getElementById('capturedImage');
    container.innerHTML = '';
    container.appendChild(img);
    document.getElementById('submitClockBtn').disabled = false;
}

async function processBulkPayment() {
    const checked = Array.from(document.querySelectorAll('#bulkPaymentModal tbody input[type=checkbox]:checked'))
        .map(chk => chk.value);
    if (checked.length === 0) {
        showToast('Select at least one employee', 'warning');
        return;
    }
    try {
        showLoading(document.querySelector('#bulkPaymentModal .btn-primary'));
        const res = await apiRequest('/api/payments/bulk_payment/', {
            method: 'POST',
            body: JSON.stringify({ employee_ids: checked })
        });
        showToast(res.message || 'Bulk payments processed successfully', 'success');
        closeModal('bulkPaymentModal');
        loadEmployees();
    } catch (err) {
        showToast('Bulk payment failed', 'error');
    } finally {
        hideLoading(document.querySelector('#bulkPaymentModal .btn-primary'));
    }
}

async function initiateIndividualPayment(e) {
    e.preventDefault();
    const empId = document.getElementById('paymentEmployee').value;
    if (!empId) {
        showToast('Choose an employee', 'warning');
        return;
    }
    try {
        showLoading(document.querySelector('#individualPaymentModal .btn-primary'));
        const data = await apiRequest('/api/payments/initiate_payment/', {
            method: 'POST',
            body: JSON.stringify({ employee_id: empId })
        });
        // open authorization page
        if (data.authorization_url) {
            window.open(data.authorization_url, '_blank');
        }
        currentPaymentReference = data.reference;
        showOTPModal();
    } catch (err) {
        showToast('Payment initialization failed', 'error');
    } finally {
        hideLoading(document.querySelector('#individualPaymentModal .btn-primary'));
    }
}

function showOTPModal() {
    document.getElementById('otpModal').classList.add('active');
    document.getElementById('otpInput').value = '';
    startOtpCountdown();
}

function startOtpCountdown() {
    const timerEl = document.getElementById('otpTimer');
    const verifyBtn = document.querySelector('#otpModal .btn-primary');
    const resendBtn = document.getElementById('resendOtpBtn');
    let time = 30;
    timerEl.textContent = time;
    verifyBtn.disabled = false;
    resendBtn.disabled = true;
    clearInterval(otpTimerInterval);
    otpTimerInterval = setInterval(() => {
        time -= 1;
        timerEl.textContent = time;
        if (time <= 0) {
            clearInterval(otpTimerInterval);
            verifyBtn.disabled = true;
            resendBtn.disabled = false;
            showToast('OTP expired. You can resend OTP now.', 'warning');
        }
    }, 1000);
}

async function handleClockIn(e) {
    e.preventDefault();
    const empId = document.getElementById('clockEmployee').value;
    const action = document.getElementById('clockAction').value;
    const canvas = document.getElementById('cameraCanvas');
    if (!empId || !action) {
        showToast('Employee and action required', 'warning');
        return;
    }
    // convert canvas to base64
    const dataUrl = canvas.toDataURL('image/png');
    const payload = {
        employee: empId,
        action: action, // expected by backend maybe 'clock_in' or 'clock_out'
        photo: dataUrl
    };
    try {
        showLoading(document.getElementById('submitClockBtn'));
        await apiRequest('/api/attendance/', {
            method: 'POST',
            body: JSON.stringify(payload)
        });
        showToast('Attendance recorded successfully', 'success');
        closeModal('clockInModal');
        loadEmployees();
    } catch (err) {
        showToast('Failed to save attendance', 'error');
    } finally {
        hideLoading(document.getElementById('submitClockBtn'));
        // stop camera
        if (cameraStream) {
            cameraStream.getTracks().forEach(t => t.stop());
            cameraStream = null;
        }
        document.getElementById('capturedImage').innerHTML = '';
        document.getElementById('submitClockBtn').disabled = true;
        document.getElementById('captureBtn').disabled = true;
    }
}

async function verifyOTP() {
    const otp = document.getElementById('otpInput').value.trim();
    if (!otp || !currentPaymentReference) {
        showToast('OTP / reference missing', 'warning');
        return;
    }
    try {
        showLoading(document.getElementById('otpModal').querySelector('.btn-primary'));
        const res = await apiRequest('/api/payments/verify_payment/', {
            method: 'POST',
            body: JSON.stringify({ reference: currentPaymentReference, otp: otp })
        });
        showToast(res.message || 'Payment verified successfully', 'success');
        closeModal('otpModal');
        closeModal('individualPaymentModal');
        loadEmployees();
    } catch (err) {
        showToast('OTP verification failed', 'error');
    } finally {
        hideLoading(document.getElementById('otpModal').querySelector('.btn-primary'));
    }
}

function clearAllNotifications() {
    const list = document.getElementById('notificationsList');
    if (list) list.innerHTML = '';
}

function exportPaymentHistory() {
    const rows = Array.from(document.querySelectorAll('#historyTableBody tr'));
    let csv = 'Date,Employee ID,Name,Bank Account,Amount,Method,Status\n';
    rows.forEach(r => {
        const cells = Array.from(r.cells).map(c => c.textContent.trim());
        csv += cells.join(',') + '\n';
    });
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'payment_history.csv';
    a.click();
    URL.revokeObjectURL(url);
}

function exportAllEmployees() {
    const rows = Array.from(document.querySelectorAll('#employeeTableBody tr'));
    let csv = 'ID,Name,Type,Location,Bank,Salary\n';
    rows.forEach(r => {
        const cells = Array.from(r.cells).map(c => c.textContent.trim());
        csv += cells.join(',') + '\n';
    });
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'employees.csv';
    a.click();
    URL.revokeObjectURL(url);
}

async function confirmExport() {
    const pwd = document.getElementById('exportPassword').value;
    if (!pwd) {
        showToast('Password required', 'warning');
        return;
    }
    try {
        showLoading(document.querySelector('#exportPasswordModal .btn-primary'));
        
        // Request export token
        const tokenRes = await apiRequest('/api/employees/request_export/', {
            method: 'POST',
            body: JSON.stringify({ password: pwd })
        });
        
        // Download CSV using token
        const exportUrl = `/api/employees/export_csv/?token=${tokenRes.token}`;
        const link = document.createElement('a');
        link.href = exportUrl;
        link.download = 'employees.csv';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        showToast('Export completed successfully', 'success');
        closeModal('exportPasswordModal');
        
    } catch (err) {
        showToast('Export failed', 'error');
    } finally {
        hideLoading(document.querySelector('#exportPasswordModal .btn-primary'));
    }
}

// ================================
// LOGIN HANDLER
// ================================

async function handleLogin(e) {
    e.preventDefault(); // FIRST thing - stop form submission
    
    const username = document.getElementById("loginUsername").value.trim();
    const password = document.getElementById("loginPassword").value.trim();

    if (!username || !password) {
        showToast("Username and password required", "error");
        return;
    }

    try {
        const response = await fetch("/api/login/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            credentials: "include",
            body: JSON.stringify({
                username: username,
                password: password
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error ||  "Login failed");
        }

        accessToken = data.access;
        sessionStorage.setItem("isLoggedIn", "true");

        document.getElementById("loginPage").classList.add("hidden");
        document.getElementById("dashboardPage").classList.remove("hidden");

        await loadCurrentUser();

        if (tbody) loadEmployees();

        showToast("Login Successful", "success");

    }
    window.addEventListener("unhandledrejection", e => {
    showToast("Something went wrong", "error");
    });

    catch (err) {
            console.error(err);
            showToast(err.message, "error");
    }
}

// ================================
// PAGE LOAD
// ================================
document.addEventListener("DOMContentLoaded", () => {
    const hamburger = document.getElementById("hamburgerBtn");
    const sidebar = document.getElementById("sidebar");

    if (hamburger && sidebar) {
        hamburger.addEventListener("click",  () => {
            sidebar.classList.toggle("active");
        });

        document.addEventListener("click", (e) => {
            if (!sidebar.contains(e.target) && !hamburger.contains(e.target)){
                sidebar.classList.remove("active");
            }
        });         
    }

    const loginForm = document.getElementById("loginForm");
    if (loginForm) loginForm.addEventListener("submit", handleLogin);

    const createForm = document.getElementById("addEmployeeForm");
    if (createForm) createForm.addEventListener("submit", handleCreateEmployee);

    const individualForm = document.getElementById("individualPaymentForm");
    if (individualForm) individualForm.addEventListener("submit", initiateIndividualPayment);

    const clockForm = document.getElementById("clockInForm");
    if (clockForm) clockForm.addEventListener("submit", handleClockIn);

    const deductionForm = document.getElementById("addDeductionForm");
    if (deductionForm) deductionForm.addEventListener("submit", handleAddDeduction);

    const companyForm = document.getElementById("addCompanyForm");
    if (companyForm) companyForm.addEventListener("submit", handleAddCompany);

    setDeleteHandler(handleDelete);
});

    // Only attempt refresh if previously logged in
        if (sessionStorage.getItem("isLoggedIn")) {
            refreshAccessToken().then(async (isLoggedIn) => {
                // `refreshAccessToken` sets `accessToken` when successful.
                if (isLoggedIn) {
                    sessionStorage.setItem("isLoggedIn", "true");
                    document.getElementById('loginPage').classList.add('hidden');
                    document.getElementById('dashboardPage').classList.remove('hidden');

                    await loadCurrentUser();
                    
                    // Show default section based on user role
                    if (currentUser) {
                        if (currentUser.is_superuser) {
                            showSection('dashboard');
                        } else if (currentUser.is_employee_admin) {
                            showSection('employees');
                        } else if (currentUser.is_payment_admin) {
                            showSection('payments');
                        } else {
                            showSection('dashboard');
                        }
                    }
                    
                    if (tbody) loadEmployees();
                }
            });
        } else {
            document.getElementById('dashboardPage').classList.add('hidden');
        }