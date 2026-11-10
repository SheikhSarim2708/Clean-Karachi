
const API_BASE_URL = "http://127.0.0.1:5000";


const registerForm = document.getElementById("register-form");

if (registerForm) {
    registerForm.addEventListener("submit", async function (event) {
        event.preventDefault();

        const name = document.getElementById("full_name").value.trim();
        const email = document.getElementById("email").value.trim();
        const password = document.getElementById("password").value;
        const confirmPassword = document.getElementById("confirm_password").value;

        if (!name || !email || !password || !confirmPassword) {
            alert("Please fill in all fields.");
            return;
        }

        if (name.length < 3) {
            alert("Name must contain at least 3 characters.");
            return;
        }

        const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

        if (!emailPattern.test(email)) {
            alert("Please enter a valid email address.");
            return;
        }

        if (password.length < 8) {
            alert("Password must contain at least 8 characters.");
            return;
        }

        if (password !== confirmPassword) {
            alert("Passwords do not match.");
            return;
        }

        const submitButton = registerForm.querySelector(
            'button[type="submit"]'
        );

        const successMessage = document.getElementById("success-message");

        submitButton.disabled = true;
        submitButton.textContent = "Creating Account...";

        successMessage.classList.remove("show");

        try {
            const response = await fetch(`${API_BASE_URL}/api/register`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                credentials: "include",
                body: JSON.stringify({
                    name: name,
                    email: email,
                    password: password
                })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || "Registration failed.");
            }

            successMessage.textContent =
                data.message || "Registration completed successfully!";

            successMessage.classList.add("show");

            registerForm.reset();

        } catch (error) {
            alert(error.message || "Unable to connect to the server.");

        } finally {
            submitButton.disabled = false;
            submitButton.textContent = "Create Account";
        }
    });
}



const loginForm = document.querySelector(".login-card form");

if (loginForm) {
    loginForm.addEventListener("submit", function (event) {
        event.preventDefault();

        const email = document.getElementById("login-email").value.trim();
        const password = document.getElementById("login-password").value;

        if (!email || !password) {
            alert("Please fill in all fields.");
            return;
        }

        const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

        if (!emailPattern.test(email)) {
            alert("Please enter a valid email address.");
            return;
        }

        if (password.length < 8) {
            alert("Password must contain at least 8 characters.");
            return;
        }

        alert("Login API integration is coming next.");
    });
}
