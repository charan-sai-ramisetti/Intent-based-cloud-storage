/* ===============================
   PAYMENTS – UPGRADE TO PRO
   =============================== */

document.addEventListener("DOMContentLoaded", () => {
  const upgradeBtn = document.getElementById("upgrade-btn");
  if (!upgradeBtn) return;

  upgradeBtn.addEventListener("click", startUpgrade);
});

function startUpgrade() {
  const upgradeBtn = document.getElementById("upgrade-btn");
  upgradeBtn.disabled = true;
  upgradeBtn.innerText = "Processing...";

  // 1️⃣ Create Razorpay order
  fetch(`${API_BASE_URL}/payments/create-order/`, {
    method: "POST",
    headers: authHeaders()
  })
    .then(res => {
      if (!res.ok) throw new Error("Order creation failed");
      return res.json();
    })
    .then(order => {
      openRazorpayCheckout(order);
    })
    .catch(err => {
      console.error(err);
      alert("Unable to start payment");
      upgradeBtn.disabled = false;
      upgradeBtn.innerText = "Upgrade";
    });
}

/* ===============================
   RAZORPAY CHECKOUT
   =============================== */
function openRazorpayCheckout(order) {
  const options = {
    key: order.razorpay_key,
    amount: order.amount,
    currency: order.currency,
    order_id: order.order_id,
    name: "TriCloud Vault",
    description: "Upgrade to PRO plan",
    theme: { color: "#2563EB" },

    handler: function (response) {
      verifyPayment(response);
    },

    modal: {
      ondismiss: function () {
        resetUpgradeButton();
      }
    }
  };

  const rzp = new Razorpay(options);
  rzp.open();
}

/* ===============================
   VERIFY PAYMENT
   =============================== */
function verifyPayment(response) {
  fetch(`${API_BASE_URL}/payments/verify/`, {
    method: "POST",
    headers: {
      ...authHeaders(),
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      razorpay_order_id: response.razorpay_order_id,
      razorpay_payment_id: response.razorpay_payment_id,
      razorpay_signature: response.razorpay_signature
    })
  })
    .then(res => {
      if (!res.ok) throw new Error("Payment verification failed");
      return res.json();
    })
    .then(() => {
      alert("🎉 Payment successful! PRO activated.");

      // Refresh dashboard state
      loadSubscriptionStatus();
      loadStorageSummary();

      // Hide upgrade button
      const upgradeBtn = document.getElementById("upgrade-btn");
      if (upgradeBtn) upgradeBtn.style.display = "none";
    })
    .catch(err => {
      console.error(err);
      alert("Payment verification failed");
      resetUpgradeButton();
    });
}

/* ===============================
   RESET BUTTON
   =============================== */
function resetUpgradeButton() {
  const upgradeBtn = document.getElementById("upgrade-btn");
  if (upgradeBtn) {
    upgradeBtn.disabled = false;
    upgradeBtn.innerText = "Upgrade";
  }
}
