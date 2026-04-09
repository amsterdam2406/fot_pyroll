function updateDashboardStats(){

    const totalStaff = employees.length;

    const guards = employees.filter(
        e => e.type === "guard"
    ).length;

    const salaryTotal = employees.reduce(
        (sum,e)=> sum + Number(e.salary || 0),0
    );

    const totalDeductions = deductions.reduce(
        (sum,d)=> sum + Number(d.amount || 0),0
    );

    const staffEl = document.getElementById("totalStaff");
    const guardsEl = document.getElementById("totalGuards");
    const paymentsEl = document.getElementById("totalPayments");
    const deductionsEl = document.getElementById("totalDeductions");

    if(staffEl) staffEl.textContent = totalStaff;
    if(guardsEl) guardsEl.textContent = guards;
    if(paymentsEl) paymentsEl.textContent = `₦${salaryTotal.toLocaleString()}`;
    if(deductionsEl) deductionsEl.textContent = `₦${totalDeductions.toLocaleString()}`;

}


async function loadAttendance(){

    try{
        const res = await apiRequest("/api/attendance/");
        const list = res.data?.results || res.data || [];
        const tbody = document.getElementById("attendanceTableBody");
        if(!tbody) return;
        tbody.replaceChildren();
        list.forEach(att => {
            const row = document.createElement("tr");
            row.innerHTML = `
            <td>${att.date || "-"}</td>
            <td>${att.employee?.id || "-"}</td>
            <td>${att.employee?.name || "-"}</td>
            <td>${att.clock_in || "-"}</td>
            <td>${att.clock_out || "-"}</td>
            <td>${att.status || "-"}</td>
            <td>
            ${att.selfie ? `<img src="${att.selfie}" width="40" alt="selfie">` : "-"}
            </td>
            `;
            tbody.appendChild(row);
        });
    }catch(err){
        console.error(err);
        showToast(`Failed to load attendance: ${err.message || "Unknown error"}`,"error");
    }
}


function renderPayments() {

    const tbody = document.getElementById("paymentsTableBody");
    if (!tbody) return;

    tbody.innerHTML = "";

    employees.forEach(emp => {

        const row = document.createElement("tr");

        row.innerHTML = `
        <td>${emp.id}</td>
        <td>${emp.name}</td>
        <td>${emp.bank_name}</td>
        <td>₦${Number(emp.salary).toLocaleString()}</td>
        <td>₦0</td>
        <td>₦${Number(emp.salary).toLocaleString()}</td>
        <td>Pending</td>
        <td>
        <button onclick="initiateIndividualPayment(${emp.id})">
        Pay
        </button>
        </td>
        `;

        tbody.appendChild(row);
    });
}

// ================================
// EXPORT EMPLOYEES
// ================================

function exportAllEmployees(){

    if(!employees.length){
        showToast("No employees to export","warning");
        return;
    }

    let csv = "ID,Name,Type,Location,Salary,Bank\n";

    employees.forEach(emp=>{
        csv += `${emp.id},${emp.name},${emp.type},${emp.location},${emp.salary},${emp.bank_name}\n`;
    });

    downloadCSV(csv,"employees.csv");

}



// ================================
// EXPORT PAYMENT HISTORY
// ================================

function exportPaymentHistory(){

    const rows = document.querySelectorAll("#paymentHistoryTableBody tr");

    if(!rows.length){
        showToast("No payment history","warning");
        return;
    }

    let csv = "Date,Employee,Amount,Status\n";

    rows.forEach(row=>{
        const cols = row.querySelectorAll("td");

        csv += `${cols[0].textContent},${cols[1].textContent},${cols[2].textContent},${cols[3].textContent}\n`;
    });

    downloadCSV(csv,"payment_history.csv");

}



// ================================
// GENERATE PAYSLIP
// ================================

function generatePayslip(){

    const emp = employees.find(e=>e.id == empId);

    if(!emp){
        showToast("Employee not found","error");
        return;
    }

    const deductionsTotal = deductions
        .filter(d=>d.employee?.id == empId)
        .reduce((sum,d)=> sum + Number(d.amount || 0),0);

    const netSalary = emp.salary - deductionsTotal;

    const content = `
    PAYSLIP

    Name: ${emp.name}
    Employee ID: ${emp.id}

    Salary: ₦${Number(emp.salary).toLocaleString()}
    Deductions: ₦${deductionsTotal.toLocaleString()}

    Net Pay: ₦${netSalary.toLocaleString()}
    `;

    const blob = new Blob([content],{type:"text/plain"});

    const url = URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.href = url;
    a.download = `payslip_${emp.name}.txt`;

    a.click();
}



// ================================
// FILTER PAYMENT HISTORY
// ================================

function filterHistory(){

    const input = document.getElementById("historyFilter");
    if(!input) return;

    const filter = input.value.toLowerCase();

    const rows = document.querySelectorAll("#paymentHistoryTableBody tr");

    rows.forEach(row=>{
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(filter) ? "" : "none";
    });

}



// ================================
// TOGGLE BULK PAYMENT CHECKBOXES
// ================================

function toggleAllBulkPayments(){

    const checkboxes = document.querySelectorAll(
        "#bulkPaymentModal tbody input[type=checkbox]"
    );

    const allChecked = Array.from(checkboxes).every(cb => cb.checked);

    checkboxes.forEach(cb => cb.checked = !allChecked);

}



// ================================
// SHOW BULK PAYMENT MODAL
// ================================

function showBulkPaymentModal(){

    populateBulkTable();

    openModal("bulkPaymentModal");

}



// ================================
// SHOW INDIVIDUAL PAYMENT MODAL
// ================================

function showIndividualPaymentModal(empId){

    const select = document.getElementById("paymentEmployee");
    if (select && empId) {
        select.value = empId;
    }

    openModal("individualPaymentModal");

}



// ================================
// RESEND OTP
// ================================

async function resendOTP(){

    if(!currentPaymentReference){
        showToast("Missing payment reference","error");
        return;
    }

    try{

        const res = await apiRequest("/api/payments/resend_otp/",{
            method:"POST",
            body:{reference: currentPaymentReference}
        });

        if(!res.success) throw new Error(res.message);

        showToast("OTP resent","success");

        startOtpCountdown();

    }catch(err){

        showToast(err.message,"error");

    }

}



// ================================
// CONFIRM EXPORT
// ================================

function confirmExport(){

    if(confirm("Export all employees?")){

        exportAllEmployees();

    }

}



// ================================
// CSV DOWNLOAD HELPER
// ================================

function downloadCSV(content,filename){

    const blob = new Blob([content],{type:"text/csv"});
    const url = URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();

} 

    document.addEventListener("DOMContentLoaded", function () {
        document.getElementById("createAccountForm")
        .addEventListener("submit", createAccount);
    });

async function createAccount(e){
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
        if (generatedIdEl) {
            generatedIdEl.textContent = res.data?.employee?.employee_id || "-";
        }

        const form = document.getElementById("createAccountForm");
        if (form) form.reset();

        await loadEmployees();
        showToast(
            res.data?.employee?.employee_id
                ? `Account created successfully. Employee ID: ${res.data.employee.employee_id}`
                : "Account created successfully",
            "success"
        );
    } catch (err) {
        showToast(err.message || "Failed to create account", "error");
    }
}

function updateDashboardStats(){

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

async function loadAttendance(){
    try{
        const res = await apiRequest("/api/attendance/");
        if (!res.success) throw new Error(res.message);
        const list = res.data?.results || res.data || [];
        const tbody = document.getElementById("attendanceTableBody");
        if(!tbody) return;
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
            ${att.clock_in_photo ? `<img src="${att.clock_in_photo}" width="40" alt="clock in">` : "-"}
            </td>
            `;
            tbody.appendChild(row);
        });
    }catch(err){
        console.error(err);
        showToast(`Failed to load attendance: ${err.message || "Unknown error"}`,"error");
    }
}

function renderPayments() {

    const tbody = document.getElementById("paymentsTableBody");
    if (!tbody) return;

    tbody.innerHTML = "";

    employees.forEach(emp => {
        const deductionsTotal = deductions
            .filter(d => d.employee === emp.id)
            .reduce((sum, d) => sum + Number(d.amount || 0), 0);
        const netSalary = Number(emp.salary || 0) - deductionsTotal;

        const row = document.createElement("tr");

        row.innerHTML = `
        <td>${emp.employee_id || emp.id}</td>
        <td>${emp.name}</td>
        <td>${emp.bank_name}</td>
        <td>₦${Number(emp.salary).toLocaleString()}</td>
        <td>₦${deductionsTotal.toLocaleString()}</td>
        <td>₦${netSalary.toLocaleString()}</td>
        <td>Pending</td>
        <td>
        <button type="button" onclick="showIndividualPaymentModal('${emp.id}')">
        Pay
        </button>
        </td>
        `;

        tbody.appendChild(row);
    });
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
            `;
            tbody.appendChild(row);
        });
    } catch (err) {
        console.error(err);
        showToast("Failed to load payment history", "error");
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
            if (recentActivity) {
                recentActivity.appendChild(item.cloneNode(true));
            }
        });
    } catch (err) {
        console.error(err);
        showToast("Failed to load notifications", "error");
    }
}

function generatePayslip(){

    const empId = document.getElementById("payslipEmployee")?.value;
    const month = document.getElementById("payslipMonth")?.value || "";
    const emp = employees.find(e => e.id == empId);

    if(!emp){
        showToast("Employee not found","error");
        return;
    }

    const deductionsTotal = deductions
        .filter(d => d.employee === emp.id)
        .reduce((sum,d)=> sum + Number(d.amount || 0),0);

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



// ============================
// EMPLOYEE SEARC

function initEmployeeSearch(){

    const search = document.getElementById("employeeSearch");

    if(!search) return;

    search.addEventListener("input", function(){

        const term = this.value.toLowerCase();

        const filtered = employees.filter(emp => 
            emp.name.toLowerCase().includes(term) ||
            emp.location.toLowerCase().includes(term) ||
            emp.type.toLowerCase().includes(term)
        );

        renderEmployees(filtered);

    });

}
pip install coverage
coverage run manage.py test
coverage report