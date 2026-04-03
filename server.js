import express from "express";
import multer from "multer";
import unzipper from "unzipper";
import fetch from "node-fetch";

const app = express();
const upload = multer({ dest: "uploads/" });

app.post("/upload", upload.single("zip"), async (req, res) => {
  try {
    const token = req.body.token;
    const repo = req.body.repo;

    const directory = await unzipper.Open.file(req.file.path);

    for (const file of directory.files) {
      if (file.type === "File") {
        const content = await file.buffer();
        const base64 = content.toString("base64");

        await fetch(`https://api.github.com/repos/${repo}/contents/${file.path}`, {
          method: "PUT",
          headers: {
            Authorization: `token ${token}`,
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            message: "upload " + file.path,
            content: base64
          })
        });
      }
    }

    res.json({ message: "✅ Upload complete to GitHub!" });

  } catch (err) {
    res.json({ message: "❌ Error uploading files" });
  }
});

app.listen(3000, () => console.log("Server running on 3000"));