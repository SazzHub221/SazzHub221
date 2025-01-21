const express = require("express");
const cors = require("cors");
const multer = require("multer");
const { spawn } = require("child_process");
const path = require("path");
const fs = require("fs");
require('dotenv').config({ path: path.join(__dirname, '..', '.env') });

const app = express();
app.use(cors());
app.use(express.json());

// Configure multer with file filtering
const storage = multer.diskStorage({
  destination: "uploads/",
  filename: (req, file, cb) => {
    const uniqueSuffix = Date.now() + '-' + Math.round(Math.random() * 1E9);
    cb(null, file.fieldname + '-' + uniqueSuffix + '.pdf');
  }
});

const upload = multer({ 
  storage: storage,
  fileFilter: (req, file, cb) => {
    if (file.mimetype === 'application/pdf') {
      cb(null, true);
    } else {
      cb(new Error('Only PDF files are allowed'));
    }
  },
  limits: {
    fileSize: 5 * 1024 * 1024 // 5MB limit
  }
});

// Cleanup old uploads periodically
const cleanupUploads = () => {
  const uploadsDir = path.join(__dirname, "uploads");
  fs.readdir(uploadsDir, (err, files) => {
    if (err) return console.error(err);
    
    files.forEach(file => {
      const filePath = path.join(uploadsDir, file);
      fs.stat(filePath, (err, stats) => {
        if (err) return console.error(err);
        
        // Delete files older than 1 hour
        if (Date.now() - stats.mtime.getTime() > 3600000) {
          fs.unlink(filePath, err => {
            if (err) console.error(err);
          });
        }
      });
    });
  });
};

setInterval(cleanupUploads, 3600000); // Run cleanup every hour

app.post("/api/upload", upload.single("pdf"), (req, res) => {
  if (!req.file) {
    return res.status(400).json({ error: "No PDF file uploaded" });
  }

  const pdfPath = req.file.path;
  const pythonProcess = spawn("python", [
    path.join(__dirname, "..", "python", "extractor.py"),
    pdfPath
  ]);

  let resultData = "";
  let errorData = "";

  pythonProcess.stdout.on("data", (data) => {
    try {
      // Clean the output string before parsing
      const cleanedData = data.toString()
        .replace(/[\u200b\ufeff\u200e]/g, '') // Remove zero-width spaces
        .replace(/[\n\r\t]/g, '') // Remove newlines, carriage returns, tabs
        .replace(/\bNaN\b/g, 'null') // Replace NaN with null
        .replace(/\bInfinity\b/g, 'null') // Replace Infinity with null
        .replace(/\bundefined\b/g, 'null') // Replace undefined with null
        .replace(/'/g, '"') // Replace single quotes with double quotes
        .replace(/\bNone\b/g, 'null') // Replace Python None with null
        .replace(/\bTrue\b/g, 'true') // Replace Python True with true
        .replace(/\bFalse\b/g, 'false') // Replace Python False with false
        .trim();

      try {
        // Try to parse the JSON
        const jsonData = JSON.parse(cleanedData);
        resultData = jsonData;
      } catch (parseError) {
        console.error('JSON Parse Error:', parseError);
        console.error('Cleaned Data:', cleanedData);
        resultData = { 
          error: 'Error parsing data from Python script',
          details: parseError.message
        };
      }
    } catch (error) {
      console.error('Error processing Python output:', error);
      console.error('Raw output:', data.toString());
      resultData = { 
        error: 'Error processing Python output',
        details: error.message
      };
    }
  });

  pythonProcess.stderr.on("data", (data) => {
    errorData += data.toString();
    console.error(`Python error: ${data}`);
  });

  pythonProcess.on("close", (code) => {
    // Delete the uploaded file after processing
    fs.unlink(pdfPath, (err) => {
      if (err) console.error(`Error deleting file: ${err}`);
    });

    if (code !== 0) {
      return res.status(500).json({ 
        error: "Processing error", 
        details: errorData 
      });
    }

    res.json(resultData);
  });
});

// Error handling middleware
app.use((err, req, res, next) => {
  if (err instanceof multer.MulterError) {
    if (err.code === 'LIMIT_FILE_SIZE') {
      return res.status(400).json({ error: 'File size is too large. Max size is 5MB' });
    }
  }
  res.status(500).json({ error: err.message });
});

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
  console.log(`Backend server running on http://localhost:${PORT}`);
});