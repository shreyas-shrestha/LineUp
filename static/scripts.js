// 🔹 Replace with your backend API URL
const API_URL = "https://lineup-fjpn.onrender.com/analyze";

document.getElementById("uploadForm").addEventListener("submit", async (e) => {
  e.preventDefault();

  const fileInput = document.getElementById("imageInput");
  if (!fileInput.files.length) {
    alert("Please select an image.");
    return;
  }

  const formData = new FormData();
  formData.append("image", fileInput.files[0]);

  document.getElementById("loading").style.display = "block";
  document.getElementById("results").innerHTML = "";

  try {
    const response = await fetch(API_URL, {
      method: "POST",
      body: formData,
    });

    const data = await response.json();
    document.getElementById("loading").style.display = "none";

    if (data.error) {
      document.getElementById("results").innerHTML = `<p style="color:red;">${data.error}</p>`;
    } else {
      document.getElementById("results").innerHTML = `
        <h2>Analysis</h2>
        <p><b>Face Shape:</b> ${data.faceShape}</p>
        <p><b>Hair Texture:</b> ${data.hairTexture}</p>
        <p><b>Hair Color:</b> ${data.hairColor}</p>
        <h3>Top 3 Recommendations</h3>
        <ul>
          ${data.recommendations.map(r => `<li><b>${r.name}:</b> ${r.reason}</li>`).join("")}
        </ul>
      `;
    }
  } catch (err) {
    console.error(err);
    document.getElementById("loading").style.display = "none";
    document.getElementById("results").innerHTML = `<p style="color:red;">Error analyzing image</p>`;
  }
});
