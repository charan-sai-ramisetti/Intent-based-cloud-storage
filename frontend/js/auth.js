// =========================
// COMMON ERROR HANDLER
// =========================
function showError(message) {
  const box = document.getElementById("login-error");
  if (!box) return;

  box.innerHTML = message;
  box.style.display = "block";

  // 🔴 reset fields when error occurs
  const emailInput = document.getElementById("loginEmail");
  const passwordInput = document.getElementById("loginPassword");

  if (emailInput) emailInput.value = "";
  if (passwordInput) passwordInput.value = "";
}

// =========================
// LOGIN
// =========================
document.addEventListener("DOMContentLoaded", () => {
  const loginForm = document.getElementById("loginForm");
  if (!loginForm) return;

  const emailInput = document.getElementById("loginEmail");
  const passwordInput = document.getElementById("loginPassword");
  const errorBox = document.getElementById("login-error");

  loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    if (errorBox) {
      errorBox.style.display = "none";
      errorBox.innerText = "";
    }

    const email = emailInput?.value.trim();
    const password = passwordInput?.value;

    if (!email || !password) {
      showError("Email and password are required.");
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/auth/login/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password })
      });

      let data = {};
      try {
        data = await response.json();
      } catch {}

      if (response.status === 401) {
        showError("Invalid email or password.");
        return;
      }

      if (response.status === 403) {
        showError(
          `Email not verified.
           <a href="/auth/resend-verification.html">Resend verification email</a>`
        );
        return;
      }

      if (!response.ok) {
        showError("Login failed. Please try again.");
        return;
      }

      // ✅ SUCCESS
      localStorage.setItem("access_token", data.access);
      localStorage.setItem("refresh_token", data.refresh);

      window.location.href = "/dashboard/dashboard.html";

    } catch {
      showError("Login request failed. Please try again.");
    }
  });
});


// =========================
// REGISTER
// =========================
window.register = function (username, email, password) {

  if (!username || !email || !password) {
    alert("All fields are required");
    return;
  }

  fetch(`${API_BASE_URL}/auth/register/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, email, password })
  })
  .then(async res => {

    const data = await res.json().catch(() => ({}));

    if (!res.ok) {

  if (data.error === "Email already exists") {
      alert("Email already registered. Try logging in.");
      document.getElementById("username").value="";
      document.getElementById("email").value="";
      document.getElementById("password").value="";
      document.getElementById("confirmPassword").value="";
      return;
  }

  if (data.error === "Username already exists") {
      alert("Username already taken. Choose another.");
      document.getElementById("username").value="";
      document.getElementById("email").value="";
      document.getElementById("password").value="";
      document.getElementById("confirmPassword").value="";
      return;
  }

}

    alert("Registration successful. Please verify your email.");

    window.location.href = "/auth/login.html";

  })
  .catch(() => {
    alert("Registration request failed. Please try again.");
  });

};