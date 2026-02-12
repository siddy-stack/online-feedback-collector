console.log("JS loaded successfully");

document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("feedbackForm");

    if (!form) return;

    form.addEventListener("submit", function (e) {
        const email = form.querySelector("input[name='email']").value;
        const comments = form.querySelector("textarea[name='comments']").value;
        const rating = form.querySelector("select[name='rating']").value;

        // Email validation
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(email)) {
            alert("Please enter a valid email address.");
            e.preventDefault();
            return;
        }

        // Rating check
        if (rating === "") {
            alert("Please select a rating.");
            e.preventDefault();
            return;
        }

        // Comment length check
        if (comments && comments.length < 10) {
            alert("Comments must be at least 10 characters long.");
            e.preventDefault();
            return;
        }
    });
});
