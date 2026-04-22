// static/js/payroll-app.js - Complete, Production-Ready Version

// ================================
// GLOBAL VARIABLES
// ================================
let employees = [];
let accessToken = null;
let currentUser = null;
let currentPaymentReference = null;
let otpTimerInterval = null;
let tbody = null;
let cameraStream = null;
let capturedImageBlob = null;
let deductions = [];
let deductionsTbody = null;
let currentEditingDeductionId = null;
let companies = [];
let currentEditingCompanyId = null;

console.log("Payroll App Loaded");

// ================================
// UTILITY FUNCTIONS
// ================================

function showLoading(btn, spinnerEl) {
    try {
        if (btn && typeof btn.disabled !== "undefined") btn.disabled = true;
        const spinner = spinnerEl || document.getElementById("globalSpinner");
        if (spinner && spinner.classList) spinner.classList.remove("hidden");
    } catch (error) {
        console.error("Error in showLoading:", error);
    }
}

function hideLoading(btn, spinnerEl) {
    try {
        if (btn && typeof btn.disabled !== "undefined") btn.disabled = false;
        const spinner = spinnerEl || document.getElementById("globalSpinner");
        if (spinner && spinner.classList) spinner.classList.add("hidden");
    } catch (error) {
        console.error("Error in hideLoading:", error);
    }
}

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
    setTimeout(() => toast.classList.add('show'), 10);
    if (duration > 0) {
        setTimeout(() => closeToast(toast.querySelector('.toast-close')), duration);
    }
}

function closeToast(btn) {
    const toast = btn.closest(".toast");
    if (!toast) return;
    toast.classList.remove("show");
    setTimeout(() => toast.remove(), 300);
}

function showSection(id) {
    document.querySelectorAll(".content-section").forEach(sec => {
        sec.classList.remove("active");
    });
    const section = document.getElementById(id);
    if (section) section.classList.add("active");

    const sidebar = document.getElementById("sidebar");
    if (sidebar && window.innerWidth <= 768) sidebar.classList.remove("active");

    document.querySelectorAll(".sidebar-menu a").forEach(link => {
        link.classList.toggle("active", link.getAttribute("onclick")?.includes(`'${id}'`));
    });
}

// ================================
// API & AUTH FUNCTIONS
// ================================

async function apiRequest(url, options = {}) {
    if (options.button?.disabled) return { success: false, message: "Action already in progress" };

    const headers = {
        ...(options.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
        ...(accessToken ? { "Authorization": `Bearer ${accessToken}` } : {}),
        ...options.headers
    };

    if (options.button) options.button.disabled = true;
    if (options.body && typeof options.body === "object") options.body = JSON.stringify(options.body);

    try {
        const response = await fetch(url, {
            method: options.method || "GET",
            credentials: "include",
            headers,
            body: options.body || null
        });

        if (response.status === 401) {
            const refreshed = await refreshAccessToken();
            if (refreshed) return apiRequest(url, options);
            logout();
            return { success: false, message: "Session expired. Please login again." };
        }

        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            const errorMessage = Array.isArray(data.error) ? data.error.join(" ") : data.detail || data.error || "Request failed";
            return { success: false, message: errorMessage };
        }
        return { success: true, data };
    } catch (err) {
        return { success: false, message: err.message || "Unknown error" };
    } finally {
        if (options.button) options.button.disabled = false;
    }
}

function buildUrl(url, params = {}) {
    const query = new URLSearchParams(params).toString();
    return query ? `${url}?${query}` : url;
}

async function refreshAccessToken() {
    try {
        const res = await fetch("/api/token/refresh/", { method: "POST", credentials: "include" });
        if (!res.ok) return false;
        const data = await res.json();
        accessToken = data.access;
        sessionStorage.setItem("accessToken", data.access);
        localStorage.setItem("accessToken", data.access);
        return true;
    } catch (err) {
        return false;
    }
}

function logout() {
    accessToken = null;
    sessionStorage.removeItem("isLoggedIn");
    sessionStorage.removeItem("accessToken");
    localStorage.removeItem("isLoggedIn");
    localStorage.removeItem("accessToken");
    document.getElementById("dashboardPage").classList.add("hidden");
    document.getElementById("loginPage").classList.remove("hidden");
}

// ================================
// DASHBOARD & STATS (FIXED - Now Defined!)
// ================================

function updateDashboardStats() {
    const totalStaff = employees.length;
    const guards = employees.filter(e => e.type === "guard").length;
    const salaryTotal = employees.reduce((sum, e) => sum + Number(e.salary || 0), 0);
    const totalDeductions = deductions.reduce((sum, d) => sum + Number(d.amount || 0), 0);

    const staffEl = document.getElementById("totalStaff");
    const guardsEl = document.getElementById("totalGuards");
    const paymentsEl = document.getElementById("totalPayments");
    const deductionsEl = document.getElementById("totalDeductions");
    const pendingPaymentsEl = document.getElementById("pendingPayments");
    const monthlyPaymentsEl = document.getElementById("monthlyPayments");

    if (staffEl) staffEl.textContent = totalStaff;
    if (guardsEl) guardsEl.textContent = guards;
    if (paymentsEl) paymentsEl.textContent = `₦${salaryTotal.toLocaleString()}`;
    if (deductionsEl) deductionsEl.textContent = `₦${totalDeductions.toLocaleString()}`;
    if (pendingPaymentsEl) pendingPaymentsEl.textContent = employees.length;
    if (monthlyPaymentsEl) monthlyPaymentsEl.textContent = `₦${salaryTotal.toLocaleString()}`;
}

// ================================
// EMPLOYEE FUNCTIONS
// ================================

async function loadEmployees(page = 1) {
    try {
        const res = await apiRequest(buildUrl("/api/employees/", { page }));
        if (!res.success) throw new Error(res.message);
        employees = res.data?.results || res.data || [];
        renderEmployees(employees);
        populateEmployeeSelect("clockEmployee");
        populateEmployeeSelect("deductionEmployee");
        populateEmployeeSelect("paymentEmployee");
        populateEmployeeSelect("payslipEmployee");
        updateDashboardStats();  // ✅ Now works because function is defined above
        renderPayments();
    } catch (err) {
        showToast(`Failed to load employees: ${err.message}`, 'error');
    }
}

function renderEmployees(list) {
    if (!tbody) return;
    tbody.innerHTML = "";
    list.forEach(emp => {
        const row = document.createElement("tr");
        row.innerHTML = `
            <td>${emp.employee_id || emp.id}</td>
            <td>${emp.name}</td>
            <td>${emp.type}</td>
            <td>${emp.location}</td>
            <td>${emp.bank_name}</td>
            <td>₦${Number(emp.salary).toLocaleString()}</td>
            <td>${emp.status || "Active"}</td>
            <td>
                <button type="button" onclick="showIndividualPaymentModal('${emp.id}')">Pay</button>
                <button type="button" onclick="showSackEmployeeModal('${emp.id}')">Sack</button>
                <button type="button" onclick="handleDelete('${emp.id}')">Delete</button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

function populateEmployeeSelect(selectId) {
    const select = document.getElementById(selectId);
    if (!select) return;
    select.innerHTML = "";
    employees.forEach(emp => {
        const opt = document.createElement("option");
        opt.value = emp.id;
        opt.textContent = `${emp.name} (${emp.type})`;
        select.appendChild(opt);
    });
}

async function handleDelete(id) {
    if (!confirm("Delete employee?")) return;
    try {
        const res = await apiRequest(`/api/employees/${id}/`, { method: "DELETE" });
        if (!res.success) throw new Error(res.message);
        await loadEmployees();
        updateDashboardStats();
        showToast('Employee deleted successfully', 'success');
    } catch (err) {
        showToast('Failed to delete employee', 'error');
    }
}

async function handleCreateEmployee(e) {
    e.preventDefault();
    const payload = {
        name: document.getElementById("newEmployeeName").value.trim(),
        type: document.getElementById("newEmployeeType").value.trim(),
        location: document.getElementById("newEmployeeLocation").value.trim(),
        salary: Number(document.getElementById("newEmployeeSalary").value),
        email: document.getElementById("newEmployeeEmail").value.trim(),
        phone: document.getElementById("newEmployeePhone").value.trim(),
        bank_name: document.getElementById("newEmployeeBankName").value.trim(),
        account_number: document.getElementById("newEmployeeAccountNumber").value.trim(),
        account_holder: document.getElementById("newEmployeeAccountHolder").value.trim(),
        join_date: document.getElementById("newEmployeeJoinDate").value
    };

    try {
        validateEmployeePayload(payload);
        showLoading(document.getElementById("createEmployeeBtn"), document.getElementById("addEmployeeSpinner"));
        await apiRequest("/api/employees/", { method: "POST", body: payload });
        showToast("Employee created successfully!", 'success');
        await loadEmployees();
        closeModal("addEmployeeModal");
    } catch (err) {
        showToast(`Error creating employee: ${err.message}`, 'error');
    } finally {
        hideLoading(document.getElementById("createEmployeeBtn"), document.getElementById("addEmployeeSpinner"));
    }
}

function validateEmployeePayload(payload) {
    if (!payload.name) throw new Error("Employee name required");
    if (!payload.type) throw new Error("Employee type required");
    if (!payload.location) throw new Error("Location required");
    if (!payload.salary || isNaN(payload.salary)) throw new Error("Valid salary required");
    if (!payload.join_date) throw new Error("Join date required");
}

function toggleCamera() {
    const markWithoutSelfie = document.getElementById("markWithoutSelfie").checked;
    const cameraSection = document.getElementById("cameraSection");
    const cameraButtons = document.getElementById("cameraButtons");
    const submitBtn = document.getElementById("submitClockBtn");
    
    if (markWithoutSelfie) {
        cameraSection.style.display = "none";
        cameraButtons.style.display = "none";
        submitBtn.disabled = false;
    } else {
        cameraSection.style.display = "block";
        cameraButtons.style.display = "flex";
        submitBtn.disabled = true;
    }
}

async function loadAttendance() {
    try {
        const res = await apiRequest("/api/attendance/");
        if (!res.success) throw new Error(res.message);
        const list = res.data?.results || res.data || [];
        const tbody = document.getElementById("attendanceTableBody");
        if (!tbody) return;
        tbody.replaceChildren();
        list.forEach(att => {
            const row = document.createElement("tr");
            row.innerHTML = `
                <td>${att.date || "-"}</td>
                <td>${att.employee_id || "-"}</td>
                <td>${att.employee_name || "-"}</td>
                <td>${att.clock_in_display || att.clock_in || "-"}</td>
                <td>${att.clock_out_display || att.clock_out || "-"}</td>
                <td>${att.status || "-"}</td>
                <td>${att.clock_in_photo ? `<img src="${att.clock_in_photo}" width="40" alt="clock in">` : "-"}</td>
            `;
            tbody.appendChild(row);
        });
    } catch (err) {
        console.error(err);
        showToast(`Failed to load attendance: ${err.message || "Unknown error"}`, "error");
    }
}

async function handleClockIn(e) {
    e.preventDefault();
    const action = document.getElementById("clockAction").value;
    const employeeId = document.getElementById("clockEmployee").value;
    const markWithoutSelfie = document.getElementById("markWithoutSelfie").checked;

    if (!markWithoutSelfie && !capturedImageBlob) {
        showToast("Please capture a photo first", "warning");
        return;
    }
    if (!employeeId) {
        showToast("Select an employee", "warning");
        return;
    }

    let url = action === "out" ? "/api/attendance/clock_out/" : "/api/attendance/clock_in/";
    let body = { employee: employeeId, date: new Date().toISOString().split('T')[0] };

    if (!markWithoutSelfie) {
        url = action === "out" ? "/api/attendance/clock_out_with_photo/" : "/api/attendance/clock_in_with_photo/";
        const photo = await blobToDataUrl(capturedImageBlob);
        body.photo = photo;
    }

    try {
        const res = await apiRequest(url, { method: "POST", body });
        if (!res.success) throw new Error(res.message || "Attendance failed");

        showToast(res.data?.message || "Attendance recorded", "success");
        capturedImageBlob = null;
        document.getElementById("capturedImage").innerHTML = "";
        document.getElementById("captureBtn").disabled = true;
        document.getElementById("submitClockBtn").disabled = !markWithoutSelfie;
        closeModal("clockInModal");
        await loadAttendance();
    } catch (err) {
        showToast(err.message, "error");
    }
}

async function startCamera() {
    const video = document.getElementById("cameraVideo");
    try {
        cameraStream = await navigator.mediaDevices.getUserMedia({ video: true });
        video.srcObject = cameraStream;
        document.getElementById("captureBtn").disabled = false;
    } catch (err) {
        showToast("Camera access denied", "error");
    }
}

function capturePhoto() {
    const video = document.getElementById("cameraVideo");
    const canvas = document.getElementById("cameraCanvas");
    const preview = document.getElementById("capturedImage");
    const submitBtn = document.getElementById("submitClockBtn");

    if (!video || !canvas || !preview) return;
    if (video.videoWidth === 0 || video.videoHeight === 0) {
        alert("Camera not ready yet. Please wait.");
        return;
    }

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    canvas.toBlob((blob) => {
        if (!blob) {
            showToast("Failed to capture image", "error");
            return;
        }
        capturedImageBlob = blob;
        const img = document.createElement("img");
        img.src = URL.createObjectURL(blob);
        img.style.width = "100%";
        img.style.borderRadius = "8px";
        preview.innerHTML = "";
        preview.appendChild(img);
        if (submitBtn) submitBtn.disabled = false;
    }, "image/jpeg", 0.8);
}

function blobToDataUrl(blob) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onloadend = () => resolve(reader.result);
        reader.onerror = reject;
        reader.readAsDataURL(blob);
    });
}

// ================================
// PAYMENT FUNCTIONS
// ================================

function renderPayments() {
    const tbody = document.getElementById("paymentsTableBody");
    if (!tbody) return;
    tbody.innerHTML = "";
    employees.forEach((emp, index) => {
        if (emp.status !== 'active') return; // Skip terminated employees
        const deductionsTotal = deductions
            .filter(d => d.employee === emp.id && d.status === 'applied')
            .reduce((sum, d) => sum + Number(d.amount || 0), 0);
        const netSalary = Number(emp.salary || 0) - deductionsTotal;
        const row = document.createElement("tr");
        row.innerHTML = `
            <td><input type="checkbox" class="payment-checkbox" value="${emp.id}"></td>
            <td>${emp.employee_id || emp.id}</td>
            <td>${emp.name}</td>
            <td>${emp.bank_name}</td>
            <td>₦${Number(emp.salary).toLocaleString()}</td>
            <td>₦${deductionsTotal.toLocaleString()}</td>
            <td>₦${netSalary.toLocaleString()}</td>
            <td>Pending</td>
            <td><button type="button" onclick="showIndividualPaymentModal('${emp.id}')">Pay</button></td>
        `;
        tbody.appendChild(row);
    });
}

async function initiateIndividualPayment(empId) {
    try {
        const res = await apiRequest('/api/payments/initiate_payment/', {
            method: 'POST',
            body: { employee_id: empId }
        });
        if (res.success && res.data.authorization_url) {
            window.open(res.data.authorization_url, '_blank');
        }
    } catch (err) {
        showToast('Failed to initiate payment', 'error');
    }
}

async function handleIndividualPaymentSubmit(e) {
    e.preventDefault();
    const employeeId = document.getElementById("paymentEmployee")?.value;
    if (!employeeId) {
        showToast("Select an employee", "warning");
        return;
    }
    await initiateIndividualPayment(employeeId);
}

async function processBulkPayment() {
    const checked = Array.from(document.querySelectorAll('#bulkPaymentModal tbody input[type=checkbox]:checked')).map(chk => chk.value);
    if (!checked.length) {
        showToast('Select at least one employee', 'warning');
        return;
    }
    try {
        showLoading(document.querySelector('#bulkPaymentModal .btn-primary'));
        const res = await apiRequest('/api/payments/bulk_payment/', {
            method: 'POST',
            body: { employee_ids: checked }
        });
        if (res.success && res.data.authorization_urls) {
            res.data.authorization_urls.forEach(url => window.open(url, '_blank'));
        }
        showToast(res.data?.message || 'Bulk payments processed', 'success');
        closeModal('bulkPaymentModal');
        await loadEmployees();
    } catch (err) {
        showToast('Bulk payment failed', 'error');
    } finally {
        hideLoading(document.querySelector('#bulkPaymentModal .btn-primary'));
    }
}

async function loadPaymentHistory() {
    try {
        const res = await apiRequest("/api/payments/");
        if (!res.success) throw new Error(res.message);
        const list = res.data?.results || res.data || [];
        const tbody = document.getElementById("historyTableBody");
        if (!tbody) return;
        tbody.innerHTML = "";
        list.forEach(payment => {
            const row = document.createElement("tr");
            row.innerHTML = `
                <td>${payment.payment_date || "-"}</td>
                <td>${payment.employee_id || payment.employee || "-"}</td>
                <td>${payment.employee_name || "-"}</td>
                <td>${payment.bank_account || "-"}</td>
                <td>₦${Number(payment.net_amount || 0).toLocaleString()}</td>
                <td>${payment.payment_method || "-"}</td>
                <td>${payment.status || "-"}</td>
                <td>
                    <button type="button" onclick="reportCashback('${payment.id}')" class="btn btn-sm btn-warning">Report Cashback</button>
                </td>
            `;
            tbody.appendChild(row);
        });
    } catch (err) {
        console.error(err);
        showToast("Failed to load payment history", "error");
    }
}

// ================================
// DEDUCTIONS FUNCTIONS
// ================================

async function loadDeductions() {
    try {
        const res = await apiRequest("/api/deductions/");
        if (!res.success) throw new Error(res.message);
        deductions = res.data?.results || res.data || [];
        renderDeductions(deductions);
        updateDashboardStats();
    } catch (err) {
        showToast(`Failed to load deductions: ${err.message}`, 'error');
    }
}

function renderDeductions(list) {
    if (!deductionsTbody) return;
    deductionsTbody.innerHTML = "";
    list.forEach(ded => {
        const row = document.createElement("tr");
        row.innerHTML = `
            <td>${ded.date || '-'}</td>
            <td>${ded.employee_id || ded.employee || '-'}</td>
            <td>${ded.employee_name || '-'}</td>
            <td>₦${Number(ded.amount || 0).toLocaleString()}</td>
            <td>${ded.reason || '-'}</td>
            <td>${ded.status || 'Pending'}</td>
            <td>
                <button type="button" onclick="editDeduction('${ded.id}')" class="btn btn-sm btn-warning">Edit</button>
                <button type="button" onclick="deleteDeduction('${ded.id}')" class="btn btn-sm btn-danger">Delete</button>
            </td>
        `;
        deductionsTbody.appendChild(row);
    });
}

async function addDeduction(e) {
    e.preventDefault();
    const employeeId = document.getElementById("deductionEmployee").value;
    const amount = Number(document.getElementById("deductionAmount").value);
    const reason = document.getElementById("deductionReason").value.trim();
    const date = new Date().toISOString().split("T")[0];

    if (!employeeId || !Number.isFinite(amount) || amount <= 0 || !reason) {
        showToast("All fields are required", "warning");
        return;
    }
    try {
        showLoading(document.getElementById("addDeductionBtn"));
        const res = await apiRequest("/api/deductions/", {
            method: "POST",
            body: { employee: employeeId, amount, reason, date }
        });
        if (!res.success) throw new Error(res.message);
        showToast("Deduction added successfully", "success");
        closeModal("addDeductionModal");
        document.getElementById("addDeductionForm").reset();
        await loadDeductions();
        await loadEmployees();
    } catch (err) {
        showToast("Failed to add deduction: " + err.message, "error");
    } finally {
        hideLoading(document.getElementById("addDeductionBtn"));
    }
}

function editDeduction(id) {
    currentEditingDeductionId = id;
    const deduction = deductions.find(d => d.id === id);
    if (!deduction) return;
    populateEmployeeSelect("editDeductionEmployee");
    openModal("editDeductionModal");
    document.getElementById("editDeductionEmployee").value = deduction.employee;
    document.getElementById("editDeductionAmount").value = deduction.amount;
    document.getElementById("editDeductionReason").value = deduction.reason;
}

async function updateDeduction(e) {
    e.preventDefault();
    if (!currentEditingDeductionId) return;
    const employeeId = document.getElementById("editDeductionEmployee").value;
    const amount = Number(document.getElementById("editDeductionAmount").value);
    const reason = document.getElementById("editDeductionReason").value.trim();
    const existingDeduction = deductions.find(d => d.id === currentEditingDeductionId);

    if (!employeeId || !Number.isFinite(amount) || amount <= 0 || !reason || !existingDeduction) {
        showToast("All fields are required", "warning");
        return;
    }
    try {
        showLoading(document.getElementById("editDeductionBtn"));
        const res = await apiRequest(`/api/deductions/${currentEditingDeductionId}/`, {
            method: "PUT",
            body: { employee: employeeId, amount, reason, date: existingDeduction.date, status: existingDeduction.status || "pending" }
        });
        if (!res.success) throw new Error(res.message);
        showToast("Deduction updated successfully", "success");
        closeModal("editDeductionModal");
        await loadDeductions();
        await loadEmployees();
    } catch (err) {
        showToast("Failed to update deduction: " + err.message, "error");
    } finally {
        hideLoading(document.getElementById("editDeductionBtn"));
    }
}

async function deleteDeduction(id) {
    if (!confirm("Are you sure you want to delete this deduction?")) return;
    try {
        const res = await apiRequest(`/api/deductions/${id}/`, { method: "DELETE" });
        if (!res.success) throw new Error(res.message);
        showToast("Deduction deleted successfully", "success");
        await loadDeductions();
        await loadEmployees();
        updateDashboardStats();
    } catch (err) {
        showToast("Failed to delete deduction: " + err.message, "error");
    }
}

// ================================
// COMPANY FUNCTIONS
// ================================

async function loadCompanies() {
    try {
        const res = await apiRequest("/api/companies/");
        if (!res.success) throw new Error(res.message);
        companies = res.data?.results || res.data || [];
        renderCompanies(companies);
    } catch (err) {
        showToast(`Failed to load companies: ${err.message}`, "error");
    }
}

function renderCompanies(list) {
    const companiesTbody = document.getElementById("companiesTableBody");
    if (!companiesTbody) return;
    companiesTbody.innerHTML = "";
    list.forEach(company => {
        const assignedGuards = company.assigned_guards_details || [];
        const guardsList = assignedGuards.map(g => `${g.employee_id} - ${g.name}`).join(', ') || 'None';
        const contact = [];
        if (company.contact_number) contact.push(company.contact_number);
        if (company.contact_email) contact.push(company.contact_email);
        const contactInfo = contact.join(', ') || 'N/A';
        
        const row = document.createElement("tr");
        row.innerHTML = `
            <td>${company.name}</td>
            <td>${company.location}</td>
            <td>${contactInfo}</td>
            <td>${guardsList}</td>
            <td>₦${Number(company.payment_to_us || 0).toLocaleString()}</td>
            <td>₦${Number(company.total_payment_to_guards || 0).toLocaleString()}</td>
            <td>₦${Number(company.profit || 0).toLocaleString()}</td>
            <td>
                <button type="button" onclick="editCompany('${company.id}')">Edit</button>
                <button type="button" onclick="deleteCompany('${company.id}')">Delete</button>
            </td>
        `;
        companiesTbody.appendChild(row);
    });
}

function editCompany(companyId) {
    const company = companies.find(item => item.id === companyId);
    if (!company) {
        showToast("Company not found", "error");
        return;
    }
    currentEditingCompanyId = company.id;
    document.getElementById("companyName").value = company.name || "";
    document.getElementById("companyLocation").value = company.location || "";
    document.getElementById("companyContactNumber").value = company.contact_number || "";
    document.getElementById("companyContactEmail").value = company.contact_email || "";
    document.getElementById("companyGuardsCount").value = company.guards_count || 0;
    document.getElementById("companyPaymentToUs").value = company.payment_to_us || 0;
    document.getElementById("companyPaymentPerGuard").value = company.payment_per_guard || 0;
    populateCompanyGuards();
    const guardSelect = document.getElementById("companyAssignedGuards");
    if (guardSelect && Array.isArray(company.assigned_guards)) {
        Array.from(guardSelect.options).forEach(option => {
            option.selected = company.assigned_guards.includes(option.value);
        });
    }
    openModal("addCompanyModal");
}

async function deleteCompany(companyId) {
    if (!confirm("Delete this company contract?")) return;
    try {
        const res = await apiRequest(`/api/companies/${companyId}/`, { method: "DELETE" });
        if (!res.success) throw new Error(res.message);
        showToast("Company deleted successfully", "success");
        if (currentUser?.is_superuser || currentUser?.role === "admin" || currentUser?.is_company_admin) {
            await loadCompanies();
        }
    } catch (err) {
        showToast(err.message || "Failed to delete company", "error");
    }
}

async function handleCreateCompany(e) {
    e.preventDefault();
    const payload = {
        name: document.getElementById("companyName").value.trim(),
        location: document.getElementById("companyLocation").value.trim(),
        contact_number: document.getElementById("companyContactNumber").value.trim(),
        contact_email: document.getElementById("companyContactEmail").value.trim(),
        guards_count: Number(document.getElementById("companyGuardsCount").value),
        payment_to_us: Number(document.getElementById("companyPaymentToUs").value),
        payment_per_guard: Number(document.getElementById("companyPaymentPerGuard").value),
        assigned_guards: Array.from(document.getElementById("companyAssignedGuards").selectedOptions).map(option => option.value)
    };
    if (!payload.name || !payload.location || !Number.isFinite(payload.guards_count) || payload.guards_count <= 0) {
        showToast("Fill all company fields correctly", "error");
        return;
    }
    try {
        const res = await apiRequest(currentEditingCompanyId ? `/api/companies/${currentEditingCompanyId}/` : "/api/companies/", {
            method: currentEditingCompanyId ? "PUT" : "POST",
            body: payload
        });
        if (!res.success) throw new Error(res.message);
        showToast(currentEditingCompanyId ? "Company updated successfully" : "Company created successfully", "success");
        document.getElementById("addCompanyForm").reset();
        currentEditingCompanyId = null;
        closeModal("addCompanyModal");
        if (currentUser?.is_superuser || currentUser?.role === "admin" || currentUser?.is_company_admin) {
            await loadCompanies();
        }
    } catch (err) {
        showToast(err.message || "Failed to create company", "error");
    }
}

function populateCompanyGuards() {
    const select = document.getElementById("companyAssignedGuards");
    if (!select) return;
    select.innerHTML = "";
    employees.filter(emp => emp.type === "guard").forEach(emp => {
        const option = document.createElement("option");
        option.value = emp.id;
        option.textContent = emp.name;
        select.appendChild(option);
    });
}

async function reinstateEmployee(recordId) {
    if (!confirm("Are you sure you want to reinstate this employee?")) return;
    try {
        const res = await apiRequest(`/api/sacked-employees/${recordId}/reinstate/`, { method: "POST" });
        if (!res.success) throw new Error(res.message);
        showToast("Employee reinstated successfully", "success");
        await loadSackedEmployees();
        await loadEmployees();
    } catch (err) {
        showToast(`Failed to reinstate employee: ${err.message}`, "error");
    }
}

async function loadSackedEmployees() {
    try {
        const res = await apiRequest("/api/sacked-employees/");
        if (!res.success) throw new Error(res.message);
        const list = res.data?.results || res.data || [];
        const tbody = document.getElementById("sackedTableBody");
        if (!tbody) return;
        tbody.innerHTML = "";
        list.forEach(record => {
            const row = document.createElement("tr");
            row.innerHTML = `
                <td>${record.employee_id || "-"}</td>
                <td>${record.employee_name || "-"}</td>
                <td>${record.employee_type || "-"}</td>
                <td>${record.date_sacked || "-"}</td>
                <td>${record.offense || "-"}</td>
                <td>${record.terminated_by_name || "-"}</td>
                <td>
                    <button type="button" onclick="reinstateEmployee('${record.id}')" class="btn btn-sm btn-success">Reinstate</button>
                </td>
            `;
            tbody.appendChild(row);
        });
    } catch (err) {
        showToast(`Failed to load sacked employees: ${err.message}`, "error");
    }
}

async function handleSackEmployee(e) {
    e.preventDefault();
    const employeeId = document.getElementById("sackEmployeeId").value;
    const offense = document.getElementById("sackReason").value.trim();
    if (!employeeId || !offense) {
        showToast("Employee and offense are required", "error");
        return;
    }
    try {
        const res = await apiRequest(`/api/employees/${employeeId}/terminate/`, {
            method: "POST",
            body: { offense }
        });
        if (!res.success) throw new Error(res.message);
        showToast("Employee terminated successfully", "success");
        closeModal("sackEmployeeModal");
        await loadEmployees();
    } catch (err) {
        showToast(err.message || "Failed to terminate employee", "error");
    }
}

// ================================
// USER & ACCOUNT FUNCTIONS
// ================================

async function loadCurrentUser() {
    try {
        const res = await apiRequest("/api/current-user/");
        if (!res.success) throw new Error(res.message);
        currentUser = res.data;
        const el = document.getElementById('currentUserName');
        if (el) el.textContent = `Welcome, ${currentUser.first_name || currentUser.username}`;
        applyRolePermissions(currentUser);
    } catch (err) {
        console.error("Failed to load user:", err);
    }
}

function applyRolePermissions(user) {
    if (!user) return;
    const visibility = [
        ["admin-controls-employee", user.is_superuser || user.role === "admin" || user.is_employee_admin],
        ["admin-controls-sacked", user.is_superuser || user.role === "admin" || user.is_employee_admin],
        ["admin-controls-companies", user.is_superuser || user.role === "admin" || user.is_company_admin],
        ["accounts", user.is_superuser || user.role === "admin"],
        ["payments", user.is_superuser || user.role === "admin" || user.is_payment_admin],
        ["deductions-section", user.is_superuser || user.role === "admin" || user.is_deduction_admin],
    ];
    visibility.forEach(([id, allowed]) => {
        const element = document.getElementById(id);
        if (element) element.style.display = allowed ? "" : "none";
    });
}

async function createAccount(e) {
    e.preventDefault();
    const fullName = document.getElementById("accountName").value.trim();
    const [firstName, ...lastNameParts] = fullName.split(/\s+/).filter(Boolean);
    const lastName = lastNameParts.join(" ");
    const salaryValue = document.getElementById("accountSalary").value.trim();
    const salary = Number(salaryValue);
    const accountNumber = document.getElementById("accountNumber").value.trim();

    if (!Number.isFinite(salary) || salary <= 0) {
        showToast("Enter a valid salary amount", "error");
        return;
    }
    if (salary >= 100000000) {
        showToast("Salary must be less than 100,000,000", "error");
        return;
    }
    if (!/^\d{10}$/.test(accountNumber)) {
        showToast("Account number must be exactly 10 digits", "error");
        return;
    }

    const payload = {
        username: document.getElementById("accountUsername").value.trim(),
        password: document.getElementById("accountPassword").value,
        email: document.getElementById("accountEmail").value.trim(),
        role: document.getElementById("accountType").value,
        first_name: firstName || "",
        last_name: lastName,
        full_name: fullName,
        location: document.getElementById("accountLocation").value.trim(),
        salary,
        phone: document.getElementById("accountPhone").value.trim(),
        bank_name: document.getElementById("accountBankName").value,
        account_number: accountNumber,
        account_holder: document.getElementById("accountHolderName").value.trim()
    };

    try {
        const res = await apiRequest("/api/register/", {
            method: "POST",
            body: payload,
            button: document.getElementById("createAccountBtn")
        });
        if (!res.success) throw new Error(res.message);

        const generatedIdEl = document.getElementById("generatedEmployeeId");
        if (generatedIdEl) generatedIdEl.textContent = res.data?.employee?.employee_id || "-";

        const form = document.getElementById("createAccountForm");
        if (form) form.reset();
        await loadEmployees();
        showToast(res.data?.employee?.employee_id ? `Account created. Employee ID: ${res.data.employee.employee_id}` : "Account created successfully", "success");
    } catch (err) {
        showToast(err.message || "Failed to create account", "error");
    }
}

// ================================
// MODAL FUNCTIONS
// ================================

function openModal(id) {
    const modal = document.getElementById(id);
    if (!modal) return;
    modal.classList.add("active");
    if (id === "clockInModal") {
        startCamera();
        document.getElementById("markWithoutSelfie").addEventListener("change", toggleCamera);
        toggleCamera(); // initial state
    }
    if (id === "addCompanyModal") {
        currentEditingCompanyId = null;
        populateCompanyGuards();
    }
}

function closeModal(id) {
    const modal = document.getElementById(id);
    if (id === "clockInModal" && cameraStream) {
        cameraStream.getTracks().forEach(track => track.stop());
    }
    if (!modal) return;
    modal.classList.remove("active");
    if (id === "bulkPaymentModal") populateBulkTable();
    if (id === "addCompanyModal") populateCompanyGuards();
}

function showAddEmployeeModal() { openModal("addEmployeeModal"); }
function showAddDeductionModal() { openModal("addDeductionModal"); }

function showSackEmployeeModal(empId) {
    const emp = employees.find(employee => employee.id === empId);
    if (!emp) {
        showToast("Employee not found", "error");
        return;
    }
    document.getElementById("sackEmployeeId").value = emp.id;
    document.getElementById("sackEmployeeName").value = emp.name;
    document.getElementById("sackDate").value = new Date().toISOString().split("T")[0];
    document.getElementById("sackReason").value = "";
    openModal("sackEmployeeModal");
}

function showIndividualPaymentModal(empId) {
    const select = document.getElementById("paymentEmployee");
    if (select && empId) select.value = empId;
    openModal("individualPaymentModal");
}

function showBulkPaymentModal() {
    populateBulkTable();
    openModal("bulkPaymentModal");
}

function populateBulkTable() {
    const tbody = document.querySelector("#bulkPaymentModal tbody");
    if (!tbody) return;
    tbody.innerHTML = "";
    employees.forEach(emp => {
        if (emp.status !== 'active') return; // Skip terminated employees
        const deductionsTotal = deductions
            .filter(d => d.employee === emp.id && d.status === 'applied')
            .reduce((sum, d) => sum + Number(d.amount || 0), 0);
        const netSalary = Number(emp.salary || 0) - deductionsTotal;
        const row = document.createElement("tr");
        row.innerHTML = `
            <td><input type="checkbox" value="${emp.id}"></td>
            <td>${emp.employee_id}</td>
            <td>${emp.name}</td>
            <td>₦${Number(emp.salary).toLocaleString()}</td>
            <td>₦${deductionsTotal.toLocaleString()}</td>
            <td>₦${netSalary.toLocaleString()}</td>
        `;
        tbody.appendChild(row);
    });
}

async function reportCashback(paymentId) {
    const cashbackAmount = prompt("Enter cashback amount to report (₦):");
    if (!cashbackAmount) return;
    
    const amount = Number(cashbackAmount);
    if (isNaN(amount) || amount <= 0) {
        showToast("Enter a valid amount", "error");
        return;
    }
    
    try {
        // Create a notification/record for the cashback
        const res = await apiRequest("/api/notifications/", {
            method: "POST",
            body: {
                message: `Cashback reported for payment ${paymentId}: ₦${amount}`,
                type: "success"
            }
        });
        
        if (res.success) {
            showToast(`Cashback of ₦${amount} reported successfully`, "success");
        } else {
            throw new Error(res.message);
        }
    } catch (err) {
        showToast("Failed to report cashback", "error");
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
            body: { reference: currentPaymentReference, otp }
        });
        startOtpCountdown();
        showToast(res.data?.message || 'Payment verified successfully', 'success');
        closeModal('otpModal');
        closeModal('individualPaymentModal');
        await loadEmployees();
    } catch (err) {
        showToast('OTP verification failed', 'error');
    } finally {
        hideLoading(document.getElementById('otpModal').querySelector('.btn-primary'));
    }
}

async function resendOTP() {
    if (!currentPaymentReference) {
        showToast("Missing payment reference", "error");
        return;
    }
    try {
        const res = await apiRequest("/api/payments/resend_otp/", {
            method: "POST",
            body: { reference: currentPaymentReference }
        });
        if (!res.success) throw new Error(res.message);
        showToast("OTP resent", "success");
        startOtpCountdown();
    } catch (err) {
        showToast(err.message, "error");
    }
}

async function loadNotifications() {
    try {
        const res = await apiRequest("/api/notifications/");
        if (!res.success) throw new Error(res.message);
        const list = res.data?.results || res.data || [];
        const container = document.getElementById("notificationsList");
        const recentActivity = document.getElementById("recentActivityList");
        if (!container) return;

        container.innerHTML = "";
        if (recentActivity) recentActivity.innerHTML = "";
        if (!list.length) {
            container.innerHTML = "<p>No notifications yet.</p>";
            if (recentActivity) recentActivity.innerHTML = "<p>No recent activity.</p>";
            return;
        }
        list.forEach(notification => {
            const item = document.createElement("div");
            item.className = "notification-item";
            item.innerHTML = `
                <strong>${notification.type || "info"}</strong>
                <p>${notification.message || ""}</p>
                <small>${notification.created_at || ""}</small>
            `;
            container.appendChild(item);
            if (recentActivity) recentActivity.appendChild(item.cloneNode(true));
        });
    } catch (err) {
        console.error(err);
        showToast("Failed to load notifications", "error");
    }
}

function clearAllNotifications() {
    const list = document.getElementById('notificationsList');
    if (list) list.innerHTML = '';
}

// ================================
// PAYSLIP & EXPORTS
// ================================

function generatePayslip() {
    const empId = document.getElementById("payslipEmployee")?.value;
    const month = document.getElementById("payslipMonth")?.value || "";
    const emp = employees.find(e => e.id == empId);
    if (!emp) {
        showToast("Employee not found", "error");
        return;
    }
    const deductionsTotal = deductions.filter(d => d.employee === emp.id).reduce((sum, d) => sum + Number(d.amount || 0), 0);
    const netSalary = Number(emp.salary || 0) - deductionsTotal;
    const preview = document.getElementById("payslipPreview");
    if (preview) {
        preview.innerHTML = `
            <div class="payslip-card">
                <h3>Payslip</h3>
                <p><strong>Month:</strong> ${month || "-"}</p>
                <p><strong>Name:</strong> ${emp.name}</p>
                <p><strong>Employee ID:</strong> ${emp.employee_id || emp.id}</p>
                <p><strong>Salary:</strong> ₦${Number(emp.salary).toLocaleString()}</p>
                <p><strong>Deductions:</strong> ₦${deductionsTotal.toLocaleString()}</p>
                <p><strong>Net Pay:</strong> ₦${netSalary.toLocaleString()}</p>
            </div>
        `;
    }
}

function exportAllEmployees() {
    if (!employees.length) {
        showToast("No employees to export", "warning");
        return;
    }
    let csv = "ID,Name,Type,Location,Salary,Bank\n";
    employees.forEach(emp => {
        csv += `${emp.id},${emp.name},${emp.type},${emp.location},${emp.salary},${emp.bank_name}\n`;
    });
    downloadCSV(csv, "employees.csv");
}

function exportPaymentHistory() {
    openModal("exportPasswordModal");
    // Set the action to export payment history after password confirmation
    document.getElementById("exportPasswordPrompt").textContent = "Enter your dashboard password to export payment history";
    window.pendingExportAction = () => {
        const rows = document.querySelectorAll("#historyTableBody tr");
        if (!rows.length) {
            showToast("No payment history", "warning");
            return;
        }
        let csv = "Date,Employee ID,Name,Bank Account,Amount,Method,Status\n";
        rows.forEach(row => {
            const cols = row.querySelectorAll("td");
            csv += `"${cols[0].textContent}","${cols[1].textContent}","${cols[2].textContent}","${cols[3].textContent}","${cols[4].textContent}","${cols[5].textContent}","${cols[6].textContent}"\n`;
        });
        downloadCSV(csv, "payment_history.csv");
    };
}

function downloadCSV(content, filename) {
    const blob = new Blob([content], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
}

function filterHistory() {
    const input = document.getElementById("historyFilter");
    if (!input) return;
    const filter = input.value.toLowerCase();
    const rows = document.querySelectorAll("#paymentHistoryTableBody tr");
    rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(filter) ? "" : "none";
    });
}

function toggleAllBulkPayments() {
    const checkboxes = document.querySelectorAll("#bulkPaymentModal tbody input[type=checkbox]");
    const allChecked = Array.from(checkboxes).every(cb => cb.checked);
    checkboxes.forEach(cb => cb.checked = !allChecked);
}

function confirmExport() {
    const password = document.getElementById("exportPassword").value;
    if (!password) {
        showToast("Enter password", "error");
        return;
    }
    
    // Verify password via API
    apiRequest("/api/verify-password/", { method: "POST", body: { password } })
        .then(res => {
            if (res.success) {
                closeModal("exportPasswordModal");
                document.getElementById("exportPassword").value = "";
                if (window.pendingExportAction) {
                    window.pendingExportAction();
                    window.pendingExportAction = null;
                }
            } else {
                showToast("Invalid password", "error");
            }
        })
        .catch(err => {
            showToast("Password verification failed", "error");
        });
}

// ================================
// SEARCH FUNCTIONALITY
// ================================

function initEmployeeSearch() {
    const search = document.getElementById("employeeSearch");
    if (!search) return;
    search.addEventListener("input", function () {
        const term = this.value.toLowerCase();
        const filtered = employees.filter(emp =>
            emp.name.toLowerCase().includes(term) ||
            emp.location.toLowerCase().includes(term) ||
            emp.type.toLowerCase().includes(term)
        );
        renderEmployees(filtered);
    });
}

// ================================
// LOGIN HANDLER
// ================================

async function handleLogin(e) {
    e.preventDefault();
    const username = document.getElementById("loginUsername").value.trim();
    const password = document.getElementById("loginPassword").value.trim();

    if (!username || !password) {
        showToast("Username and password required", "error");
        return;
    }
    try {
        const response = await fetch("/api/login/", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "include",
            body: JSON.stringify({ username, password })
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Login failed");

        accessToken = data.access;
        sessionStorage.setItem("isLoggedIn", "true");
        sessionStorage.setItem("accessToken", data.access);
        localStorage.setItem("isLoggedIn", "true");
        localStorage.setItem("accessToken", data.access);

        document.getElementById("loginPage").classList.add("hidden");
        document.getElementById("dashboardPage").classList.remove("hidden");

        await loadCurrentUser();
        await loadEmployees();
        populateEmployeeSelect("clockEmployee");
        populateEmployeeSelect("deductionEmployee");
        populateEmployeeSelect("paymentEmployee");
        populateEmployeeSelect("payslipEmployee");
        await loadDeductions();
        await loadAttendance();
        if (typeof loadPaymentHistory === "function") await loadPaymentHistory();
        if (typeof loadNotifications === "function") await loadNotifications();
        await loadSackedEmployees();
        if (currentUser?.is_superuser || currentUser?.role === "admin" || currentUser?.is_company_admin) {
            await loadCompanies();
        }
        showToast("Login Successful", "success");
    } catch (err) {
        console.error(err);
        showToast(err.message, "error");
    }
}

// ================================
// INITIALIZATION
// ================================

document.addEventListener("DOMContentLoaded", () => {
    initEmployeeSearch();
    accessToken = localStorage.getItem("accessToken") || sessionStorage.getItem("accessToken");
    tbody = document.getElementById("employeeTableBody");
    deductionsTbody = document.getElementById("deductionsTableBody");

    const hamburger = document.getElementById("hamburgerBtn");
    const sidebar = document.getElementById("sidebar");

    if (hamburger && sidebar) {
        hamburger.addEventListener("click", (e) => {
            e.preventDefault();
            e.stopPropagation();
            sidebar.classList.toggle("active");
        });
        document.addEventListener("click", (e) => {
            if (!sidebar.contains(e.target) && !hamburger.contains(e.target)) {
                sidebar.classList.remove("active");
            }
        });
    }

    // Restore session if logged in
    if (localStorage.getItem("isLoggedIn") || sessionStorage.getItem("isLoggedIn")) {
        Promise.resolve(Boolean(accessToken) || refreshAccessToken()).then(async (isLoggedIn) => {
            if (isLoggedIn) {
                document.getElementById('loginPage').classList.add('hidden');
                document.getElementById('dashboardPage').classList.remove('hidden');
                await loadCurrentUser();
                if (tbody) await loadEmployees();
                await loadDeductions();
                await loadAttendance();
                if (typeof loadPaymentHistory === "function") await loadPaymentHistory();
                if (typeof loadNotifications === "function") await loadNotifications();
                await loadSackedEmployees();
                if (currentUser?.is_superuser || currentUser?.role === "admin" || currentUser?.is_company_admin) {
                    await loadCompanies();
                }
            }
        });
    }

    // Form event listeners
    const clockForm = document.getElementById("clockInForm");
    if (clockForm) clockForm.addEventListener("submit", handleClockIn);

    const individualPaymentForm = document.getElementById("individualPaymentForm");
    if (individualPaymentForm) individualPaymentForm.addEventListener("submit", handleIndividualPaymentSubmit);

    const sackForm = document.getElementById("sackEmployeeForm");
    if (sackForm) sackForm.addEventListener("submit", handleSackEmployee);

    const companyForm = document.getElementById("addCompanyForm");
    if (companyForm) companyForm.addEventListener("submit", handleCreateCompany);

    const deductionForm = document.getElementById("addDeductionForm");
    if (deductionForm) deductionForm.addEventListener("submit", addDeduction);

    const editForm = document.getElementById("editDeductionForm");
    if (editForm) editForm.addEventListener("submit", updateDeduction);

    const createAccountForm = document.getElementById("createAccountForm");
    if (createAccountForm) createAccountForm.addEventListener("submit", createAccount);
});