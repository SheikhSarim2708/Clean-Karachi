
const API_BASE_URL = "http://127.0.0.1:5000";

const complaintForm = document.querySelector(".complaint-form-card form");

if (complaintForm) {

    const categorySelect = document.getElementById("category");
    const areaSelect = document.getElementById("area");
    const imageInput = document.getElementById("complaint-image");

    function showMessage(message, success = false) {
        let messageBox = document.getElementById("complaint-message");

        if (!messageBox) {
            messageBox = document.createElement("div");
            messageBox.id = "complaint-message";
            complaintForm.prepend(messageBox);
        }

        messageBox.textContent = message;
        messageBox.style.padding = "12px";
        messageBox.style.marginBottom = "15px";
        messageBox.style.borderRadius = "6px";
        messageBox.style.backgroundColor = success ? "#d4edda" : "#f8d7da";
        messageBox.style.color = success ? "#155724" : "#721c24";
    }

    async function loadCategories() {
        try {
            const response = await fetch(`${API_BASE_URL}/api/categories`, {
                credentials: "include"
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || "Unable to load categories.");
            }

            const categories = data.categories || data;

            categorySelect.innerHTML = '<option value="">Select a category</option>';

            categories.forEach(function (category) {
                const option = document.createElement("option");
                option.value = category.id;
                option.textContent = category.name;
                categorySelect.appendChild(option);
            });

        } catch (error) {
            console.error("Category error:", error);
            showMessage("Could not load categories. Please login and refresh.");
        }
    }

    async function loadAreas() {
        try {
            const response = await fetch(`${API_BASE_URL}/api/areas`, {
                credentials: "include"
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || "Unable to load areas.");
            }

            const areas = data.areas || data;

            areaSelect.innerHTML = '<option value="">Select your area</option>';

            areas.forEach(function (area) {
                const option = document.createElement("option");
                option.value = area.id;
                option.textContent = area.name;
                areaSelect.appendChild(option);
            });

        } catch (error) {
            console.error("Area error:", error);
            showMessage("Could not load areas. Please login and refresh.");
        }
    }

    loadCategories();
    loadAreas();

    complaintForm.addEventListener("submit", async function (event) {
        event.preventDefault();

        const title = document.getElementById("complaint-title").value.trim();
        const category = categorySelect.value;
        const area = areaSelect.value;
        const address = document.getElementById("address").value.trim();
        const description = document.getElementById("description").value.trim();
        const image = imageInput.files[0];

        if (!title || !category || !area || !description) {
            showMessage("Please fill in all required fields.");
            return;
        }

        if (title.length > 150) {
            showMessage("Complaint title cannot exceed 150 characters.");
            return;
        }

        if (image) {
            const allowedTypes = ["image/jpeg", "image/png"];

            if (!allowedTypes.includes(image.type)) {
                showMessage("Only JPG, JPEG and PNG images are allowed.");
                return;
            }

            if (image.size > 5 * 1024 * 1024) {
                showMessage("Image size must not exceed 5 MB.");
                return;
            }
        }

        const submitButton = complaintForm.querySelector('button[type="submit"]');

        submitButton.disabled = true;
        submitButton.textContent = "Submitting...";

        const formData = new FormData();

        formData.append("title", title);
        formData.append("category_id", category);
        formData.append("area_id", area);
        formData.append("address_detail", address);
        formData.append("description", description);

        if (image) {
            formData.append("image", image);
        }

        try {
            const response = await fetch(`${API_BASE_URL}/api/complaints`, {
                method: "POST",
                credentials: "include",
                body: formData
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || "Complaint submission failed.");
            }

            showMessage(
                `Complaint submitted successfully! Complaint ID: ${data.complaint_id}`,
                true
            );

            complaintForm.reset();

        } catch (error) {
            console.error("Complaint submission error:", error);
            showMessage(error.message || "Unable to connect to server.");
        } finally {
            submitButton.disabled = false;
            submitButton.textContent = "Submit Complaint";
        }
    });
}
