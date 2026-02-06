console.log("JS loaded successfully");

// Optional form validation (for feedback form page)
document.addEventListener("DOMContentLoaded", function () {
    const form = document.querySelector("form");

    if (form) {
        form.addEventListener("submit", function (e) {
            const rating = document.querySelector("select[name='rating']");
            if (rating && rating.value === "") {
                alert("Please select a rating");
                e.preventDefault();
            }
        });
    }
});
