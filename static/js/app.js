document.addEventListener("DOMContentLoaded", () => {
  const search = document.getElementById("tableSearch");
  const table = document.getElementById("complaintTable");
  if (search && table) {
    search.addEventListener("input", () => {
      const q = search.value.toLowerCase().trim();
      table.querySelectorAll("tbody tr").forEach(row => {
        row.hidden = !row.innerText.toLowerCase().includes(q);
      });
    });
  }
  const photo = document.getElementById("photo");
  const fileName = document.getElementById("fileName");
  if (photo && fileName) {
    photo.addEventListener("change", () => {
      const file = photo.files && photo.files[0];
      fileName.textContent = file ? `Selected: ${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)` : "";
      if (file && file.size > 5 * 1024 * 1024) {
        fileName.textContent = "That file is larger than 5 MB. Please choose a smaller image.";
        photo.value = "";
      }
    });
  }
});
