// GLOBAL VARIABLES
let employees = [];
let accessToken = null; // access token in memory only
let currentUserName = null;
let currentUser = null;
let currentPaymentReference = null;
let otpTimerInterval = null;
let tbody = null;
let deleteHandler = null;
let cameraStream = null;
let capturedImageBlob = null;
let deductions = [];
let deductionsTbody = null;
let currentEditingDeductionId = null;
let companies = [];
let currentEditingCompanyId = null;
let payments = [];
let user = null;
let loginLocked = false;
let loginInProgress = false;

console.log("Script loaded");

function debounce(fn, delay = 300) {
    let timeout;
    return (...args) => {
        clearTimeout(timeout);
        timeout = setTimeout(() => fn(...args), delay);
    };
}


function updateDashboardStats() {
    const totalEmployees = employees?.length || 0;

    const totalDeductions = (deductions || []).reduce((sum, d) => {
        return sum + Number(d.amount || 0);
    }, 0);

    const totalSalaries = (employees || []).reduce((sum, emp) => {
        return sum + Number(emp.salary || 0);
    }, 0);

    const netPay = totalSalaries - totalDeductions;

    const totalEmployeesEl = document.getElementById("totalEmployees");
    const totalDeductionsEl = document.getElementById("totalDeductions");
    const totalSalariesEl = document.getElementById("totalSalaries");
    const netPayEl = document.getElementById("netPay");

    if (totalEmployeesEl) totalEmployeesEl.textContent = totalEmployees.toLocaleString();
    if (totalDeductionsEl) totalDeductionsEl.textContent = totalDeductions.toLocaleString();
    if (totalSalariesEl) totalSalariesEl.textContent = totalSalaries.toLocaleString();
    if (netPayEl) netPayEl.textContent = netPay.toLocaleString();
}


function showLoading(btn, spinnerEl) {
    try {
        // Disable button safely
        if (btn && typeof btn.disabled !== "undefined") {
            btn.disabled = true;
        }
        // Get spinner element
        const spinner = spinnerEl || document.getElementById("globalSpinner");
        // Show spinner if it exists
        if (spinner && spinner.classList) {
            spinner.classList.remove("hidden");
        } else {
            console.warn("Spinner element not found.");
        }
    } catch (error) {
        console.error("Error in showLoading:", error);
    }
}

function hideLoading(btn, spinnerEl) {
    try {
        // Enable button safely
        if (btn && typeof btn.disabled !== "undefined") {
            btn.disabled = false;
        }
        // Get spinner element
        const spinner = spinnerEl || document.getElementById("globalSpinner");
        // Hide spinner if it exists
        if (spinner && spinner.classList) {
            spinner.classList.add("hidden");
        } else {
            console.warn("Spinner element not found.");
        }
    } catch (error) {
        console.error("Error in hideLoading:", error);
    }
}

function showSection(id) {

    document.querySelectorAll(".content-section").forEach(sec => {
        sec.classList.remove("active");
    });

    const section = document.getElementById(id);

    if(section){
        section.classList.add("active");
    }

    const sidebar = document.getElementById("sidebar");
    if (sidebar && window.innerWidth <= 768) {
        sidebar.classList.remove("active");
    }

    document.querySelectorAll(".sidebar-menu a").forEach(link => {
        link.classList.toggle("active", link.getAttribute("onclick")?.includes(`'${id}'`));
    });

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


    // Trigger animation
    setTimeout(() => toast.classList.add('show'), 10);

    // Auto remove
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


function validateEmployeePayload(payload) {

    if (!payload.name) throw new Error("Employee name required");

    if (!payload.type) throw new Error("Employee type required");

    if (!payload.location) throw new Error("Location required");

    if (!payload.salary || isNaN(payload.salary)) {
        throw new Error("Valid salary required");
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
        if (element) {
            element.style.display = allowed ? "" : "none";
        }
    });

}

// LOAD ATTENDANCE (DRF GET API)
async function loadAttendance() {
    try {
        const res = await apiRequest("/api/attendance/");

        if (!res.success) {
            throw new Error(res.message || "Failed to fetch attendance");
        }

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
                <td>
                    ${att.clock_in_photo 
                        ? `<img src="${att.clock_in_photo}" width="40" alt="clock in">`
                        : "-"
                    }
                </td>
            `;

            tbody.appendChild(row);
        });

    } catch (err) {
        console.error("Load attendance error:", err);
        showToast(err.message || "Failed to load attendance", "error");
    }
}


async function handleClockIn(e) {
    e.preventDefault();

    const action = document.getElementById("clockAction").value;
    const employeeId = document.getElementById("clockEmployee").value;

    if (!employeeId) {
        showToast("Select an employee", "warning");
        return;
    }

    if (!capturedImageBlob) {
        showToast("Please capture a photo first", "warning");
        return;
    }

    const url = action === "out"
        ? "/api/attendance/clock_out_with_photo/"
        : "/api/attendance/clock_in_with_photo/";

    try {
        const photo = await blobToDataUrl(capturedImageBlob);

        const res = await apiRequest(url, {
            method: "POST",
            body: {
                employee_id: employeeId,
                photo: photo
            }
        });

        if (!res.success) {
            throw new Error(res.message || "Attendance failed");
        }

        showToast(res.data?.message || "Attendance recorded", "success");

        // reset UI
        capturedImageBlob = null;
        document.getElementById("capturedImage").innerHTML = "";
        document.getElementById("captureBtn").disabled = true;
        document.getElementById("submitClockBtn").disabled = true;

        closeModal("clockInModal");

        await loadAttendance();

    } catch (err) {
        console.error("Clock in error:", err);
        showToast(err.message || "Attendance error", "error");
    }
}


async function startCamera() {
    const video = document.getElementById("cameraVideo");

    try {
        cameraStream = await navigator.mediaDevices.getUserMedia({
            video: true
        });

        video.srcObject = cameraStream;

        document.getElementById("captureBtn").disabled = false;

    } catch (err) {
        console.error("Camera error:", err);
        showToast("Camera access denied", "error");
    }
}

function capturePhoto() {
    const video = document.getElementById("cameraVideo");
    const canvas = document.getElementById("cameraCanvas");
    const preview = document.getElementById("capturedImage");
    const submitBtn = document.getElementById("submitClockBtn");

    if (!video || !canvas || !preview) {
        console.error("Camera elements not found");
        showToast("Camera setup error", "error");
        return;
    }

    if (video.videoWidth === 0 || video.videoHeight === 0) {
        showToast("Camera not ready yet", "warning");
        return;
    }

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    const ctx = canvas.getContext("2d");
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    canvas.toBlob((blob) => {
        if (!blob) {
            console.error("Failed to capture image");
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


function logout() {
    accessToken = null;
    sessionStorage.removeItem("isLoggedIn");
    sessionStorage.removeItem("accessToken");
    localStorage.removeItem("isLoggedIn");
    localStorage.removeItem("accessToken");

    document.getElementById("dashboardPage").classList.add("hidden");
    document.getElementById("loginPage").classList.remove("hidden");
}

async function apiRequest(url, options = {}) {
    if (options.button?.disabled) {
        return { success: false, message: "Action already in progress" };
    }
    
    const token = localStorage.getItem("accessToken");

    const headers = {
        ...(options.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
        ...(token ? { "Authorization": `Bearer ${token}` } : {}),
        ...options.headers
    };

    if (options.body && typeof options.body === "object" && !(options.body instanceof FormData)) {
        options.body = JSON.stringify(options.body);
    }

    try {
        const response = await fetch(url, {
            method: options.method || "GET",
            headers,
            body: options.body || null
        });

        // Handle token expiry
        if (response.status === 401) {
            const refreshed = await refreshAccessToken();
            if (refreshed) return apiRequest(url, options);

            logout();
            return { success: false, message: "Session expired. Please login again." };
        }

        const data = await response.json().catch(() => ({}));

        return response.ok
            ? { success: true, data }
            : { success: false, message: data.detail || data.error || "Request failed" };

    } catch (err) {
        console.error("API error:", err);
        return { success: false, message: err.message || "Network error" };
    }
}

function buildUrl(url, params = {}) { 
        const query = new URLSearchParams(params).toString(); 
        return query ? `${url}?${query}` : url; 
    }


// ================================
// EMPLOYEE CRUD
// ================================

async function loadEmployees(page=1) {

    try {
        const res = await apiRequest(buildUrl("/api/employees/", {page}));
        if (!res.success) throw new Error(res.message);
        employees = res.data?.results || res.data || [];
        renderEmployees(employees);
        updateUIAfterEmployeeLoad();
    } catch (err) { 
        showToast(`Failed to load employees: ${err.message}`, "error");
    }
}


function updateUIAfterEmployeeLoad() {
    populateEmployeeSelect("clockEmployee");
    populateEmployeeSelect("deductionEmployee");
    populateEmployeeSelect("paymentEmployee");
    populateEmployeeSelect("payslipEmployee");

    updateDashboardStats();
    if (typeof renderPayments === "function") renderPayments();
}

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
        const row = document.createElement("tr");
        row.innerHTML = `
            <td>${company.name}</td>
            <td>${company.location}</td>
            <td>${Array.isArray(company.assigned_guards) ? company.assigned_guards.length : 0}</td>
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

async function handleDelete(id) {
    if (!confirm("Delete employee?")) return;
    try {
        const res =await apiRequest(`/api/employees/${id}/`, { method: "DELETE" });
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
    const res = await apiRequest("/api/employees/", {
            method: "POST",
            body: payload
        });
            if (!res.success) {
                throw new Error(res.message);
            }

    // await apiRequest("/api/employees/", {
    //         method: "POST",
    //         body: payload
    //     });

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

// // fetch logged user
// ======

async function loadCurrentUser() {
    try {
        const res = await apiRequest("/api/current-user/");
        if (!res.success) throw new Error(res.message);

        currentUser = res.data;
        const el = document.getElementById('currentUserName');
        if (el){
            el.textContent = `Welcome, ${currentUser.first_name || currentUser.username}`;
        }
            applyRolePermissions(currentUser);
    } catch (err) {
        console.error("Failed to load user:", err);
    }
}


async function loadDeductions() {
    try {
        const res = await apiRequest("/api/deductions/"); 
        if (!res.success) throw new Error(res.message);

        // Store and render
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

// function populateDeductionEmployeeSelect() {
//     const select = document.getElementById("deductionEmployee");
//     if (!select) return;

//     select.innerHTML = "";

//     employees.forEach(emp => {
//         const option = document.createElement("option");
//         option.value = emp.id;
//         option.textContent = `${emp.name} (${emp.type})`;
//         select.appendChild(option);
//     });
// }


// Open Edit Deduction Modal and pre-fill fields
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

function populateEmployeeSelect(selectId) {
    const select = document.getElementById(selectId);
    if (!select) return;

    select.innerHTML = '<option value="">Select Employee</option>';

    employees.forEach(emp => {
        const option = document.createElement("option");
        option.value = emp.id;
        option.textContent = `${emp.name} (${emp.type})`;
        select.appendChild(option);
    });
}


// Submit edited deduction
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
            body: {
                employee: employeeId,
                amount,
                reason,
                date: existingDeduction.date,
                status: existingDeduction.status || "pending"
            }
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

// ================================
// EMPLOYEE TABLE RENDERING


    function renderEmployees(list = []) {
        const tableBody = document.getElementById("employeesTableBody");
        if (!tableBody) return;

        tableBody.innerHTML = "";
        list.forEach(emp => {
            if (!emp) return;
            const row = document.createElement("tr");

            row.innerHTML = `
                <td>${emp.employee_id ?? emp.id ?? "-"}</td>
                <td>${emp.name ?? "-"}</td>
                <td>${emp.type ?? "-"}</td>
                <td>${emp.location ?? "-"}</td>
                <td>${emp.bank_name ?? "-"}</td>
                <td>₦${Number(emp.salary ?? 0).toLocaleString()}</td>
                <td>${emp.status || "Active"}</td>
                <td>
                    <button type="button" onclick="initiateIndividualPayment('${emp.id}')">Pay</button>
                    <button type="button" onclick="showSackEmployeeModal('${emp.id}')">Sack</button>
                    <button type="button" onclick="handleDelete('${emp.id}')">Delete</button>
                </td>
            `;

            tableBody.appendChild(row);
        });
    }

    function populateBulkTable() {
        const tbody = document.querySelector("#bulkPaymentModal tbody");
        if (!tbody) return;
        tbody.innerHTML = "";
        employees.forEach(emp => {
        const row = document.createElement("tr");
        row.innerHTML = `
            <td><input type="checkbox" value="${emp.id}"></td>
            <td>${emp.name}</td>
            <td>${emp.salary}</td>
        `;
        tbody.appendChild(row);
    });

}

function populateCompanyGuards() {

    const select = document.getElementById("companyAssignedGuards");

    if (!select) return;

    select.innerHTML = "";

    employees
        .filter(emp => emp.type === "guard")
        .forEach(emp => {

            const option = document.createElement("option");

            option.value = emp.id;
            option.textContent = emp.name;

            select.appendChild(option);

        });

}

async function handleCreateCompany(e) {
    e.preventDefault();

    const payload = {
        name: document.getElementById("companyName").value.trim(),
        location: document.getElementById("companyLocation").value.trim(),
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

// =======
// MODA=====

function openModal(id) {
    const modal = document.getElementById(id);
    if (!modal) return;
    modal.classList.add("active");
    if (id === "clockInModal") {
        startCamera();
    }
    if (id === "addCompanyModal") {
        currentEditingCompanyId = null;
        populateCompanyGuards();
    }
}


function closeModal(id) {
    const modal = document.getElementById(id);
    if (id ===  "clockInModal" && cameraStream){
        cameraStream.getTracks().forEach(track => track.stop());
    }
    if (!modal) return;
    modal.classList.remove("active");

    // optionak modal initializations
    if (id === "bulkPaymentModal") {
        populateBulkTable();
    }

    if (id === "addCompanyModal") {
        populateCompanyGuards();
    }
}
function showAddEmployeeModal() {
    openModal("addEmployeeModal");
}

function showAddDeductionModal() {
    openModal("addDeductionModal");
}

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
                <td>-</td>
            `;
            tbody.appendChild(row);
        });
    } catch (err) {
        showToast(`Failed to load sacked employees: ${err.message}`, "error");
    }
}





// Bulk Payment
async function processBulkPayment() {
    const checked = Array.from(document.querySelectorAll('#bulkPaymentModal tbody input[type=checkbox]:checked'))
        .map(chk => chk.value);
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
        // Paystack URLs and references come from backend
        if(res.success && res.data.authorization_urls) {
            // Open all payment links in new tabs
            res.data.authorization_urls.forEach(url => window.open(url, '_blank'));
        }
        showToast(res.data?.message || 'Bulk payments processed', 'success');
        closeModal('bulkPaymentModal');
        loadEmployees();
    } catch (err) {
        showToast('Bulk payment failed', 'error');
    } finally {
        hideLoading(document.querySelector('#bulkPaymentModal .btn-primary'));
    }
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

// ================================
// LOGIN HANDLER
// ================================
async function handleLogin(e) {
    e.preventDefault();

    if (loginLocked) {
        showToast("Too many failed attempts. Try again later.", "error");
        return;
    }

    if (loginInProgress) return;

    loginLocked = true;
    loginInProgress = true;

    setTimeout(() => {
        loginLocked = false;
    }, 5 * 60 * 1000);

    const username = document.getElementById("loginUsername").value.trim();
    const password = document.getElementById("loginPassword").value.trim();

    if (!username || !password) {
        showToast("Username and password required", "error");
        loginInProgress = false;
        return;
    }

    try {
        const response = await fetch("/api/login/", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Login failed");
        }
        // localStorage.setItem("accessToken", data.access);
        accessToken = data.access;
        // window.accessToken = data.access;

        // localStorage.setItem("isLoggedIn", "true");

        localStorage.setItem("accessToken", data.access);
        localStorage.setItem("refreshToken", data.refresh);

        sessionStorage.setItem("accessToken", data.access);
        sessionStorage.setItem("isLoggedIn", "true");

        accessToken = data.access;
        


        document.getElementById("loginPage").classList.add("hidden");
        document.getElementById("dashboardPage").classList.remove("hidden");
        
        await loadCurrentUser();
        await loadEmployees();
        await loadDeductions();
        await loadAttendance();
        await loadSackedEmployees();

        if (currentUser?.is_superuser ||
            currentUser?.role === "admin" ||
            currentUser?.is_company_admin
        ) {
            await loadCompanies();
        }

        showToast("Login Successful", "success");
    } catch (err) {
        console.error(err);
        showToast(err.message, "error");
    } finally {
        loginInProgress = false;
    }
}


// ================================
// PAGE LOAD DOMcont
// ================================
document.addEventListener("DOMContentLoaded", async () => {
    tbody = document.getElementById("employeesTableBody");
    deductionsTbody = document.getElementById("deductionsTableBody");

    const storedToken = localStorage.getItem("accessToken") || 
                        sessionStorage.getItem("accessToken");
    if (storedToken) {
        accessToken = storedToken;
        console.log("Token loaded from storage:", accessToken ? "Yes" : "No");
    }

    function initEmployeeSearch() {
    const input = document.getElementById("employeeSearch");
    if (!input) return;

    input.addEventListener("input", debounce((e) => {
        const value = e.target.value.toLowerCase();

        const filtered = employees.filter(emp =>
            emp.name?.toLowerCase().includes(value) ||
            emp.type?.toLowerCase().includes(value)
        );

        renderEmployees(filtered);
    }, 300));
}


    initEmployeeSearch();

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
    
    const isLoggedInStorage = localStorage.getItem("isLoggedIn") || sessionStorage.getItem("isLoggedIn");
    let isLoggedIn = false;
    if (isLoggedInStorage) {
        if (accessToken) {
            isLoggedIn = true;
        } else {
            isLoggedIn = await refreshAccessToken();
        }

        if (isLoggedIn) {
            console.log("User is logged in, loading dashboard...");
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
    }

    if (!isLoggedIn) {
        localStorage.removeItem("isLoggedIn");
        sessionStorage.removeItem("isLoggedIn");
        
        document.getElementById("dashboardPage").classList.add("hidden");
        document.getElementById("loginPage").classList.remove("hidden");

        console.log("Token invalid or expired, showing login page");
    }

    const clockForm = document.getElementById("clockInForm");
    if (clockForm) 
        clockForm.addEventListener("submit", handleClockIn);

    const individualPaymentForm = document.getElementById("individualPaymentForm");
    if (individualPaymentForm) 
        individualPaymentForm.addEventListener("submit", handleIndividualPaymentSubmit);

    const sackForm = document.getElementById("sackEmployeeForm");
    if (sackForm) {
        sackForm.addEventListener("submit", handleSackEmployee);
    }

    const companyForm = document.getElementById("addCompanyForm");
    if (companyForm) {
        companyForm.addEventListener("submit", handleCreateCompany);
    }

    // Existing employee load
    // if (tbody) loadEmployees().then(() => populateDeductionEmployeeSelect());
    const deductionForm = document.getElementById("addDeductionForm");
    if (deductionForm) deductionForm.addEventListener("submit", addDeduction);
    const editForm = document.getElementById("editDeductionForm");
    if (editForm) editForm.addEventListener("submit", updateDeduction);
});
    

async function loadPaymentHistory() {
    const tbody = document.getElementById("historyTableBody");
    if (!tbody) return;

    try {
        const res = await apiRequest("/api/payments/");
        if (!res.success) throw new Error(res.message);

        const list = res.data?.results || res.data || [];
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
            `;
            tbody.appendChild(row);
        });
    } catch (err) {
        console.error(err);
        showToast("Failed to load payment history", "error");
    }
}

async function loadNotifications() {
    const container = document.getElementById("notificationsList");
    if (!container) return;

    try {
        const res = await apiRequest("/api/notifications/");
        if (!res.success) throw new Error(res.message);

        const list = res.data?.results || res.data || [];
        container.innerHTML = "";

        if (!list.length) {
            container.innerHTML = "<p>No notifications yet.</p>";
            return;
        }

        list.forEach(notification => {
            const item = document.createElement("div");
            const type = notification?.type || "info";
            const createdAt = notification?.created_at
                ? new Date(notification.created_at).toLocaleString()
                : "";

            item.className = `notification ${type}`;

            const title = document.createElement("strong");
            title.textContent = type.charAt(0).toUpperCase() + type.slice(1);

            const message = document.createElement("p");
            message.textContent = notification?.message || "";

            item.appendChild(title);
            item.appendChild(message);

            if (createdAt) {
                const time = document.createElement("div");
                time.className = "time";
                time.textContent = createdAt;
                item.appendChild(time);
            }

            container.appendChild(item);
        });
    } catch (err) {
        container.innerHTML = "<p>Failed to load notifications.</p>";
        showToast(`Failed to load notifications: ${err.message}`, "error");
    }
}

async function refreshAccessToken() {
    try {
        const refreshToken = localStorage.getItem("refreshToken");

        if (!refreshToken) {
            return false;
        }

        const res = await fetch("/api/token/refresh/", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ refresh: refreshToken })
        });

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