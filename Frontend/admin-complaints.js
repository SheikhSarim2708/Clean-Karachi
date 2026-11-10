
const API_BASE_URL = "http://127.0.0.1:5000";

const searchInput = document.querySelector(".admin-complaint-search");
const statusFilter = document.getElementById("status-filter");
const categoryFilter = document.getElementById("category-filter");
const areaFilter = document.getElementById("area-filter");
const emptyState = document.querySelector(".admin-complaint-empty");
const complaintSection = document.querySelector(".admin-complaint-list");

let complaintsContainer;
let staffMembers = [];

function getArray(data, key) {
    if (Array.isArray(data)) return data;
    return data[key] || [];
}

function showMessage(message, isError = false) {
    let box = document.getElementById("admin-message");

    if (!box) {
        box = document.createElement("p");
        box.id = "admin-message";
        complaintSection.appendChild(box);
    }

    box.textContent = message;
    box.style.color = isError ? "red" : "green";
}

async function apiRequest(url, options = {}) {
    const response = await fetch(`${API_BASE_URL}${url}`, {
        credentials: "include",
        ...options
    });

    const data = await response.json();

    if (response.status === 401 || response.status === 403) {
        window.location.href = "login.html";
        throw new Error("Please login as administrator.");
    }

    if (!response.ok) {
        throw new Error(data.message || "Request failed.");
    }

    return data;
}

complaintsContainer = document.createElement("div");
complaintsContainer.id = "admin-complaints-container";
complaintSection.appendChild(complaintsContainer);

async function loadFilters() {
    try {
        const [categoryData, areaData] = await Promise.all([
            apiRequest("/api/categories"),
            apiRequest("/api/areas")
        ]);

        const categories = getArray(categoryData, "categories");
        const areas = getArray(areaData, "areas");

        categories.forEach(category => {
            const option = document.createElement("option");
            option.value = category.id;
            option.textContent = category.name;
            categoryFilter.appendChild(option);
        });

        areas.forEach(area => {
            const option = document.createElement("option");
            option.value = area.id;
            option.textContent = area.name;
            areaFilter.appendChild(option);
        });

    } catch (error) {
        showMessage(error.message, true);
    }
}

async function loadStaff() {
    try {
        const data = await apiRequest("/api/admin/users?role=staff");
        staffMembers = getArray(data, "users");
    } catch (error) {
        showMessage("Unable to load staff members: " + error.message, true);
    }
}

function updateOverview(complaints, total) {
    const cards = document.querySelectorAll(".complaint-overview-card h2");

    const pending = complaints.filter(c => c.status === "pending").length;
    const assigned = complaints.filter(c => c.status === "assigned").length;
    const resolved = complaints.filter(c => c.status === "resolved").length;

    if (cards[0]) cards[0].textContent = total;
    if (cards[1]) cards[1].textContent = pending;
    if (cards[2]) cards[2].textContent = assigned;
    if (cards[3]) cards[3].textContent = resolved;
}

function createComplaintCard(complaint) {
    const card = document.createElement("article");
    card.className = "admin-complaint-card";

    const title = document.createElement("h3");
    title.textContent = complaint.title || "Untitled Complaint";

    const details = document.createElement("p");
    details.textContent =
        `#${complaint.id} | ${complaint.category || "N/A"} | ${complaint.area || "N/A"}`;

    const status = document.createElement("p");
    status.textContent = `Status: ${(complaint.status || "pending").replace("_", " ")}`;

    const date = document.createElement("p");
    date.textContent = complaint.created_at
        ? new Date(complaint.created_at).toLocaleDateString()
        : "";

    card.append(title, details, status, date);

    const staffSelect = document.createElement("select");
    staffSelect.className = "assign-staff-select";

    const defaultOption = document.createElement("option");
    defaultOption.value = "";
    defaultOption.textContent = "Select Staff Member";
    staffSelect.appendChild(defaultOption);

    staffMembers.forEach(staff => {
        const option = document.createElement("option");
        option.value = staff.id;
        option.textContent = staff.name || staff.email;
        staffSelect.appendChild(option);
    });

    const assignButton = document.createElement("button");
    assignButton.type = "button";
    assignButton.textContent = "Assign Staff";
    assignButton.className = "assign-staff-button";

    assignButton.addEventListener("click", async () => {
        const staffId = staffSelect.value;

        if (!staffId) {
            alert("Please select a staff member.");
            return;
        }

        assignButton.disabled = true;
        assignButton.textContent = "Assigning...";

        try {
            await apiRequest(
                `/api/admin/complaints/${complaint.id}/assign`,
                {
                    method: "PUT",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        staff_id: Number(staffId)
                    })
                }
            );

            alert("Staff assigned successfully!");
            loadComplaints();

        } catch (error) {
            alert(error.message);
            assignButton.disabled = false;
            assignButton.textContent = "Assign Staff";
        }
    });

    card.append(staffSelect, assignButton);

    return card;
}

async function loadComplaints() {
    complaintsContainer.innerHTML = "";
    emptyState.style.display = "none";

    const params = new URLSearchParams();

    params.set("page", "1");
    params.set("page_size", "100");

    if (statusFilter.value !== "all") {
        params.set("status", statusFilter.value);
    }

    if (categoryFilter.value !== "all") {
        params.set("category_id", categoryFilter.value);
    }

    if (areaFilter.value !== "all") {
        params.set("area_id", areaFilter.value);
    }

    if (searchInput.value.trim()) {
        params.set("search", searchInput.value.trim());
    }

    try {
        const data = await apiRequest(
            `/api/admin/complaints?${params.toString()}`
        );

        const complaints = getArray(data, "complaints");
        const total = data.total ?? complaints.length;

        updateOverview(complaints, total);

        if (complaints.length === 0) {
            emptyState.style.display = "block";
            return;
        }

        complaints.forEach(complaint => {
            complaintsContainer.appendChild(
                createComplaintCard(complaint)
            );
        });

    } catch (error) {
        showMessage(error.message, true);
    }
}

statusFilter.addEventListener("change", loadComplaints);
categoryFilter.addEventListener("change", loadComplaints);
areaFilter.addEventListener("change", loadComplaints);
searchInput.addEventListener("input", loadComplaints);

async function initializePage() {
    await loadFilters();
    await loadStaff();
    await loadComplaints();
}

initializePage();
